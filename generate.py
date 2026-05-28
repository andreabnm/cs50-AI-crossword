import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var in self.domains:
            for word in list(self.domains[var]):
                if var.length != len(word):
                    self.domains[var].remove(word)
    
    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False 
        # check if there are overlaps between the 2 variables 
        overlap = self.crossword.overlaps[(x, y)] 
        if overlap: 
            # following the overlap rule remove the words in x domain 
            # for which there are no corresponding compliant word in y domain 
            for word_X in list(self.domains[x]): 
                compliant_words_y = [word_y for word_y in self.domains[y]
                                     if word_X[overlap[0]] == word_y[overlap[1]]]
                if not compliant_words_y: 
                    self.domains[x].remove(word_X) 
                    revised = True
        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None: 
            arc_queue = [item for item, value in self.crossword.overlaps.items() if value != None] 
        else:
            arc_queue = arcs
            
        # while not empty 
        while arc_queue:
            # dequeue next arc 
            x, y = arc_queue.pop(0) 
            if self.revise(x, y): 
                # if revising the variables the domain of x 
                # is emptied, return False as there is no solution 
                if not self.domains[x]:
                    return False 
                # if not empty, every neighbors of X (apart from Y) 
                # represent another possible arc that could be affected by the change
                # so hit as to be enqueued in the list 
                x_neighbors = self.crossword.neighbors(x) - {y} 
                for z in x_neighbors: 
                    arc_queue.append((z, x)) 

        return True
    
    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        return len(assignment) == len(self.domains)

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # check all values are distinct
        # compare length of assignment with its distinct copy
        if len(assignment) != len(set(assignment.values())):
            return False

        for var in assignment:
            # correct length
            if var.length != len(assignment[var]):
                return False
            
            # no conflict with neighbors
            neighbors = self.crossword.neighbors(var)
            for y in neighbors:
                if y in assignment:
                    if not self.satisfy_overlap(var, assignment[var], y, assignment[y]):
                        return False
                
        return True
    
    def satisfy_overlap(self, x, word_x, y, word_y):
        overlap = self.crossword.overlaps[(x,y)]
        if word_x[overlap[0]] == word_y[overlap[1]]:
            return True
        return False

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        values = {}
        neighbors = self.crossword.neighbors(var)

        # for every word in the domain of the variable,
        # calculate how many values in each neighbour
        # get ruled out and insert then in a dictionary that
        # can be comfortably sorted
        for x in self.domains[var]: 
            for y in neighbors:
                overlap = self.crossword.overlaps[(var, y)]
                not_compliant_words_y = [word_y for word_y in self.domains[y]
                                        if x[overlap[0]] != word_y[overlap[1]]]
                if x not in values:
                    values[x] = len(not_compliant_words_y)
                else:
                    values[x] += len(not_compliant_words_y)

        # return the list of values in increasing order of values
        # that get ruled out 
        return sorted(values, key=values.get)
    
    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned_vars = {var: domain for var, domain in self.domains.items()
                           if var not in assignment}
        # get the shortest domain and get only
        # the variables with that domain length
        min_domain_len = min(len(values) for values in unassigned_vars.values())
        min_domain_vars = [var for var, domain in unassigned_vars.items()
                           if len(domain) == min_domain_len]

        # for every var found, I search the one with the 
        # max number of neighbors
        max_neighbors = 0
        high_degree_var = None
        for var in min_domain_vars:
            neighbors = self.crossword.neighbors(var)
            if len(neighbors) > max_neighbors:
                max_neighbors = len(neighbors)
                high_degree_var = var

        return high_degree_var

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        unassigned_var = self.select_unassigned_variable(assignment)
        domain_values = self.order_domain_values(unassigned_var, assignment)
        for word in domain_values:
            assignment[unassigned_var] = word
            if self.consistent(assignment):
                result = self.backtrack(assignment)
                if result:
                    return result
            self.assignment_complete.pop(unassigned_var)
                
        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
