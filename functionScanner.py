import ast
import getopt
import sys
import csv
from bs4 import BeautifulSoup
import re

class scanner(ast.NodeVisitor):
    def __init__(self, html, parametic_poly):
        self.funcs = {}
        self.funcs["funcs"] = []
        self.funcs["classes"] = {}
        self.classnames = []
        self.parametic_poly = parametic_poly
        if html != None:
            self.soup = BeautifulSoup(html, features="html.parser")

    def visit_FunctionDef(self, node):
        if len(self.classnames) == 0 and not node.name.startswith("_") and node.name not in self.funcs["funcs"] and self.parametic_poly == True and self.check_polymorphism(node.name, node.lineno):
            self.funcs["funcs"].append(node.name)
        elif len(self.classnames) == 1 and not node.name.startswith("_") and node.name not in self.funcs["classes"][self.classnames[len(self.classnames)  - 1]] and self.parametic_poly == True and self.check_polymorphism(node.name, node.lineno):
            self.funcs["classes"][self.classnames[len(self.classnames)  - 1]].append(node.name)
        elif len(self.classnames) == 0 and not node.name.startswith("_") and node.name not in self.funcs["funcs"] and self.parametic_poly == False:
            self.funcs["funcs"].append(node.name)
        elif len(self.classnames) == 1 and not node.name.startswith("_") and node.name not in self.funcs["classes"][self.classnames[len(self.classnames)  - 1]] and self.parametic_poly == False:
            self.funcs["classes"][self.classnames[len(self.classnames)  - 1]].append(node.name)

    def visit_ClassDef(self, node):
        self.classnames.append(node.name)

        if self.classnames[len(self.classnames) - 1] not in self.funcs["classes"]:
            self.funcs["classes"][self.classnames[len(self.classnames) - 1]] = []

        self.generic_visit(node)

        self.classnames.pop(len(self.classnames) - 1)
    
    def finalize(self):
        deletekeys = []
        for c in self.funcs["classes"]:
            if len(self.funcs["classes"][c]) == 0:
                deletekeys.append(c)
        for c in deletekeys:
            del self.funcs["classes"][c]

    def print_to_csv(self, csvfile):
        keys = ["class", "func"]
        values = []
        for func in self.funcs["funcs"]:
            values.append(["None", func])
        for c in self.funcs["classes"]:
            for func in self.funcs["classes"][c]:
                values.append([c, func])

        if len(values) > 0:
            with open(csvfile, "w") as csvcontent:
                writer = csv.writer(csvcontent)
                writer.writerow(keys)
                writer.writerows(values)

    def check_polymorphism(self, name, lineno):
        spans = self.soup.find_all("span", text = re.compile(" *" + str(lineno)))
        if len(spans) > 1 or len(spans) == 0:
            return False
        else:
            p = spans[0].next_sibling
            while(p != None and p.name != "span"):
                if hasattr(p, "xid") and hasattr(p, "title") and p.string == name:
                    types = p["title"].split(" / ")
                    count = 0
                    returnvalues = {}
                    for t in types:
                        if "?" not in t and " -> " in t:
                            sig = t.split(" -> ")
                            if "|" in sig[0] and "{" in sig[0] and "}" in sig[0]:
                                return True
                            if sig[1] not in returnvalues:
                                returnvalues[sig[1]] = sig[0]
                            elif returnvalues[sig[1]] != sig[0]:
                                count += 1
                    if count > 0:
                        return True
                    else:
                        return False
                p = p.next_sibling
        return False
        



if __name__ == "__main__":
    sourcefile = None
    csvfile = None
    parametic_poly = False
    htmlfile = None
    try:
        opts, args = getopt.getopt(sys.argv[1:],"-h-s:-c:-p-t:",["source=", "csvfile=", "parametic-poly", "typeres="])
    except getopt.GetoptError:
        print("Unsupportable arguments, please see functionScanner.py -h")
        sys.exit(-1)
    for opt, arg in opts:
        if opt == '-h':
            print("Usage:\n-s/--source <Python Source File> : Indicate the path of Python source file")
            print("-c/--csvfile <CSV File> : Write the result into the csv file")
            sys.exit()
        elif opt in ("-s", "--source"):
            sourcefile = arg
        elif opt in ("-c", "--csvfile"):
            csvfile = arg
        elif opt in ("-p", "--parametic-poly"):
            parametic_poly = True
        elif opt in ("-t", "--typeres"):
            htmlfile = arg

    if sourcefile != None:
        source = open(sourcefile, "r").read()
        root = ast.parse(source)
        html = open(htmlfile, "r")
        visitor = scanner(html, parametic_poly)
        visitor.visit(root)
        visitor.finalize()
        print(visitor.funcs)
        if csvfile != None:
            visitor.print_to_csv(csvfile)
