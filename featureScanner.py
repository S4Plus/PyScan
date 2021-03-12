import ast
import astpretty
from bs4 import BeautifulSoup
import re
import sys, getopt
from prettytable import PrettyTable
import configparser
import pandas as pd
import os
import datetime
import time
import signal

class TimeoutError(Exception):
    def __init__(self, msg):
        super(TimeoutError, self).__init__()
        self.msg = msg
 
 
def time_out(interval, callback):
    def decorator(func):
        def handler(signum, frame):
            raise TimeoutError("Scanner Timed Out. This may because it encounters a very large file.")
 
        def wrapper(*args, **kwargs):
            try:
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(interval)     
                result = func(*args, **kwargs)
                signal.alarm(0)         
                return result
            except TimeoutError:
                callback()
        return wrapper
    return decorator
 
 
def timeout_callback():
    print("Scanner Timed Out. This may because it encounters a very large file.")

class analyzer(ast.NodeVisitor):
    def __init__(self, setup, lib):
        self.featuremap = {}

        self.setup = {}
        self.setup["introspection_funcs"] = setup["introspection_funcs"].split(", ")
        self.setup["introspection_attrs"] = setup["introspection_attrs"].split(", ")
        self.setup["reflection_funcs"] = setup["reflection_funcs"].split(", ")
        self.setup["recursion_limit"] = int(setup["recursion_limit"])
        self.lib = lib

        #useful info
        self.funcnames = [[]]
        self.classchildren = {}
        self.classparent = {}
        self.classes = []
        self.classattrs = []
        self.classnames = []
        self.funcsum = {}
        self.funcsum["funcs"] = {}
        self.funcsum["classes"] = {}
        self.check_args = False
        self.isleftvalue = False
        self.modules = []
        self.modulealias = {}


        #Function Call and Argument Passing 
        self.featuremap["FCAP"] = {}
        self.featuremap["FCAP"]["kwonlyargs"] = 0
        self.featuremap["FCAP"]["kwarg"] = 0
        self.featuremap["FCAP"]["posonlyargs"] = 0
        self.featuremap["FCAP"]["multiple_return"] = 0
        self.featuremap["FCAP"]["loop"] = {}
        self.featuremap["FCAP"]["loop"]["while"] = 0
        self.featuremap["FCAP"]["loop"]["for"] = 0
        self.featuremap["FCAP"]["loop"]["continue"] = 0
        self.featuremap["FCAP"]["loop"]["break"] = 0
        self.featuremap["FCAP"]["recursion"] = 0
        self.featuremap["FCAP"]["nested_function"] = 0
        self.featuremap["FCAP"]["exception"] = {}
        self.featuremap["FCAP"]["exception"]["try"] = 0
        self.featuremap["FCAP"]["exception"]["raise"] = 0
        self.featuremap["FCAP"]["exception"]["with_args"] = 0
        self.featuremap["FCAP"]["packing_and_unpacking"] = {}
        self.featuremap["FCAP"]["packing_and_unpacking"]["packing"] = 0
        self.featuremap["FCAP"]["packing_and_unpacking"]["unpacking"] = 0
        self.featuremap["FCAP"]["decorator"] = 0

        #Type System
        self.featuremap["TS"] = {}
        self.featuremap["TS"]["first_class_function"] = {}
        self.featuremap["TS"]["first_class_function"]["function_as_parameter"] = 0
        self.featuremap["TS"]["first_class_function"]["function_as_returnvalue"] = 0
        self.featuremap["TS"]["first_class_function"]["function_assignedto_var"] = 0
        self.featuremap["TS"]["gradual_typing"] = 0

        #Evaluation Strategy
        self.featuremap["ES"] = {}
        self.featuremap["ES"]["generator"] = 0

        #Object Oriented Programming
        self.featuremap["OOP"] = {}
        self.featuremap["OOP"]["nested_class"] = 0
        self.featuremap["OOP"]["inheritance"] = {}
        self.featuremap["OOP"]["inheritance"]["single"] = 0
        self.featuremap["OOP"]["inheritance"]["multiple"] = 0
        self.featuremap["OOP"]["inheritance"]["hierarchical"] = 0
        self.featuremap["OOP"]["inheritance"]["multilevel"] = 0
        self.featuremap["OOP"]["inheritance"]["diamond"] = 0
        self.featuremap["OOP"]["polymorphism"] = {}
        self.featuremap["OOP"]["polymorphism"]["parametic"] = 0
        self.featuremap["OOP"]["encapsulation"] = {}
        self.featuremap["OOP"]["encapsulation"]["protected"] = {}
        self.featuremap["OOP"]["encapsulation"]["protected"]["var"] = 0
        self.featuremap["OOP"]["encapsulation"]["protected"]["method"] = 0
        self.featuremap["OOP"]["encapsulation"]["private"] = {}
        self.featuremap["OOP"]["encapsulation"]["private"]["var"] = 0
        self.featuremap["OOP"]["encapsulation"]["private"]["method"] = 0

        #Data Structure
        self.featuremap["DS"] = {}
        self.featuremap["DS"]["list_comprehension"] = 0
        self.featuremap["DS"]["heterogeneous_list"] = {}
        self.featuremap["DS"]["heterogeneous_list"]["constant_index"] = 0
        self.featuremap["DS"]["heterogeneous_list"]["variable_index"] = 0
        self.featuremap["DS"]["heterogeneous_tuple"] = {}
        self.featuremap["DS"]["heterogeneous_tuple"]["constant_index"] = 0
        self.featuremap["DS"]["heterogeneous_tuple"]["variable_index"] = 0

        #MetaProgramming
        self.featuremap["MP"] = {}
        self.featuremap["MP"]["introspection"] = 0
        self.featuremap["MP"]["reflection"] = 0
        self.featuremap["MP"]["metaclass"] = 0

        #read standard libs
        polymorphsim_file = self.lib +"/standard_polymorphism.csv"
        func_file = self.lib + "/standard_funcs.csv"
        self.polys = pd.read_csv(polymorphsim_file, header = None, names = ["filepath", "class", "func"], sep = ",")
        self.funcs = pd.read_csv(func_file, header = None, names = ["filepath", "class", "func"], sep = ",")



    def visit_Import(self, node):
        if len(node.names) > 0:
            for n in node.names:
                if hasattr(n, "name") and hasattr(n, "asname"):
                    self.modules.append(n.name)
                if hasattr(n, "name") and hasattr(n, "asname") and n.asname != None:
                    self.modulealias[n.asname] = n.name

        
    
    def visit_FunctionDef(self, node):
        if len(self.funcnames[len(self.funcnames) - 1]) > 0:
            self.featuremap["FCAP"]["nested_function"] += 1
        self.funcnames[len(self.funcnames) - 1].append(node.name)
        
        #add call info
        if len(self.classnames) == 0 and node.name not in self.funcsum["funcs"]:
            self.funcsum["funcs"][node.name] = []
        elif len(self.classnames) > 0 and self.classnames[len(self.classnames) - 1] != None and node.name not in self.funcsum["classes"][self.classnames[len(self.classnames) - 1]]:
            self.funcsum["classes"][self.classnames[len(self.classnames) - 1]][node.name] = []

        
        #check return value annotations
        if node.returns != None:
            self.featuremap["TS"]["gradual_typing"] += 1
        
        #check protected and private methods
        if node.name.startswith("__") and len(self.classnames) > 0 and node.name != "__init__":
            self.featuremap["OOP"]["encapsulation"]["private"]["method"] += 1
        elif node.name.startswith("_") and len(self.classnames) > 0 and node.name != "__init__":
            self.featuremap["OOP"]["encapsulation"]["protected"]["method"] += 1

        #check decorators
        if len(node.decorator_list) > 0:
            self.featuremap["FCAP"]["decorator"] += len(node.decorator_list)

        self.generic_visit(node)
        self.funcnames[len(self.funcnames) - 1].pop(len(self.funcnames[len(self.funcnames) - 1]) - 1)

    def visit_ClassDef(self, node):
        if len(self.classnames) > 0:
            self.featuremap["OOP"]["nested_class"] += 1
        self.classnames.append(node.name)
        self.classattrs.append([])
        self.funcnames.append([])

        #add call info
        if node.name not in self.funcsum["classes"]:
            self.funcsum["classes"][node.name] = {}

        #check single and multiple inheritance
        if len(node.bases) == 1 and hasattr(node.bases[0], "id") and node.bases[0].id != "object":
            self.featuremap["OOP"]["inheritance"]["single"] += 1
        elif len(node.bases) > 1:
            self.featuremap["OOP"]["inheritance"]["multiple"] += 1

        #build inheritance graph
        if len(node.bases) > 0 and hasattr(node, "name"):
            for i in node.bases:
                if hasattr(i, "id") and i.id != "object":
                    if i.id not in self.classchildren:
                        self.classchildren[i.id] = []
                    self.classchildren[i.id].append(node.name)
                    if node.name not in self.classparent and node.name != "object":
                        self.classparent[node.name] = []
                    self.classparent[node.name].append(i.id)
        if hasattr(node, "name"):
            self.classes.append(node.name)

        #check metaclass
        for i in node.keywords:
            if hasattr(i, "arg") and i.arg == "metaclass":
                self.featuremap["MP"]["metaclass"] += 1

        self.generic_visit(node)

        self.classattrs.pop(len(self.classattrs) - 1)
        self.classnames.pop(len(self.classnames) - 1)
        self.funcnames.pop(len(self.funcnames) - 1)


    def visit_Return(self, node):
        multiple = False
        #check multiple return
        if hasattr(node.value, "elts") and len(node.value.elts) > 1:
            multiple = True
            self.featuremap["FCAP"]["multiple_return"] += 1

        #check if return value is a function
        if multiple:
            for i in node.value.elts:
                if hasattr(i, "id") and self.check_func(i.id, node.lineno):
                    self.featuremap["TS"]["first_class_function"]["function_as_returnvalue"] += 1
        else:
            if hasattr(node.value, "id") and self.check_func(node.value.id, node.lineno):
                self.featuremap["TS"]["first_class_function"]["function_as_returnvalue"] += 1

        self.generic_visit(node)

    def visit_arguments(self, node):
        if len(node.kwonlyargs) > 0:
            self.featuremap["FCAP"]["kwonlyargs"] += len(node.kwonlyargs)
        if len(node.posonlyargs) > 0:
            self.featuremap["FCAP"]["posonlyargs"] += len(node.posonlyargs)
        if node.kwarg != None:
            self.featuremap["FCAP"]["kwarg"] += 1
        if len(node.defaults) > 0:
            self.featuremap["FCAP"]["kwarg"] += len(node.defaults)
        if node.vararg != None:
            self.featuremap["FCAP"]["packing_and_unpacking"]["packing"] += 1

        for i in node.args:
            if i.annotation != None:
                self.featuremap["TS"]["gradual_typing"] += 1

        self.generic_visit(node)

    def visit_While(self, node):
        self.featuremap["FCAP"]["loop"]["while"] += 1
        self.generic_visit(node)
    
    def visit_For(self, node):
        self.featuremap["FCAP"]["loop"]["for"] += 1
        self.generic_visit(node)

    def visit_Continue(self, node):
        self.featuremap["FCAP"]["loop"]["continue"] += 1

    def visit_Break(self, node):
        self.featuremap["FCAP"]["loop"]["break"] += 1
    
    def visit_Call(self, node):

        #add call info
        if (len(self.funcnames[0]) != 0 and hasattr(node.func, "id") and 
            len(self.classnames) == 0 and [node.func.id] not in self.funcsum["funcs"][self.funcnames[0][len(self.funcnames[0]) - 1]]):
            self.funcsum["funcs"][self.funcnames[0][len(self.funcnames[0]) - 1]].append([node.func.id])
        elif (len(self.funcnames[len(self.funcnames) - 1]) != 0 and hasattr(node.func, "id") and 
            len(self.classnames) > 0 and [node.func.id] not in self.funcsum["classes"][self.classnames[len(self.classnames) - 1]][self.funcnames[len(self.funcnames) - 1][len(self.funcnames[len(self.funcnames) - 1]) - 1]]):
            self.funcsum["classes"][self.classnames[len(self.classnames) - 1]][self.funcnames[len(self.funcnames) - 1][len(self.funcnames[len(self.funcnames) - 1]) - 1]].append([node.func.id])
        else:
            if (len(self.funcnames[0]) != 0 and hasattr(node.func, "attr") and hasattr(node.func, "value") and hasattr(node.func.value, "id") and 
                len(self.classnames) == 0 and [self.check_type(node.func.value.id, node.func.value.lineno), node.func.attr] not in self.funcsum["funcs"][self.funcnames[0][len(self.funcnames[0]) - 1]]):
                self.funcsum["funcs"][self.funcnames[0][len(self.funcnames[0]) - 1]].append([self.check_type(node.func.value.id, node.func.value.lineno), node.func.attr])
            elif (len(self.funcnames[len(self.funcnames) - 1]) != 0 and hasattr(node.func, "attr") and hasattr(node.func, "value") and hasattr(node.func.value, "id") and 
                len(self.classnames) > 0 and [self.check_type(node.func.value.id, node.func.value.lineno), node.func.attr] not in self.funcsum["classes"][self.classnames[len(self.classnames) - 1]][self.funcnames[len(self.funcnames) - 1][len(self.funcnames[len(self.funcnames) - 1]) - 1]]):
                self.funcsum["classes"][self.classnames[len(self.classnames) - 1]][self.funcnames[len(self.funcnames) - 1][len(self.funcnames[len(self.funcnames) - 1]) - 1]].append([self.check_type(node.func.value.id, node.func.value.lineno), node.func.attr])


        #check unpacking arguments
        for i in node.args:
            if type(i) == ast.Starred:
                self.featuremap["FCAP"]["packing_and_unpacking"]["unpacking"] += 1

        for i in node.keywords:
            if type(i) == ast.keyword and i.arg == None:
                self.featuremap["FCAP"]["packing_and_unpacking"]["unpacking"] += 1
            elif type(i) == ast.keyword:
                self.featuremap["FCAP"]["kwarg"] += 1

        #check if parameter is a function
        for i in node.args:
            if hasattr(i, "id") and self.check_func(i.id, i.lineno):
                print(i.lineno)
                self.featuremap["TS"]["first_class_function"]["function_as_parameter"] += 1
            elif self.check_outside_func(i):
                print(i.lineno)            
                self.featuremap["TS"]["first_class_function"]["function_as_parameter"] += 1

        #check introspection
        if hasattr(node.func, "id") and node.func.id in self.setup["introspection_funcs"]:
            self.featuremap["MP"]["introspection"] += 1
        
        #check reflection
        if hasattr(node.func, "id") and node.func.id in self.setup["reflection_funcs"]:
            self.featuremap["MP"]["reflection"] += 1

        #type which can be either introspection or reflection
        if hasattr(node.func, "id") and node.func.id == "type" and len(node.args) == 1:
            self.featuremap["MP"]["introspection"] += 1
        elif hasattr(node.func, "id") and node.func.id == "type" and len(node.args) == 3:
            self.featuremap["MP"]["reflection"] += 1
        

        #check parametic polymorphism
        if hasattr(node.func, "id") and self.check_polymorphism(node.func.id, node.func.lineno):
            self.featuremap["OOP"]["polymorphism"]["parametic"] += 1
        elif type(node.func) == ast.Attribute and self.check_outside_polymorphism(node.func):
            self.featuremap["OOP"]["polymorphism"]["parametic"] += 1
        

        self.generic_visit(node)    

    def visit_Try(self, node):
        self.featuremap["FCAP"]["exception"]["try"] += 1
        self.generic_visit(node)

    def visit_Raise(self, node):
        self.featuremap["FCAP"]["exception"]["raise"] += 1
        if hasattr(node.exc, "args"):
            for i in node.exc.args:
                self.check_args = True
                self.generic_visit(i)
                self.check_args = False

    def visit_Name(self, node):
        if hasattr(node, "id") and self.check_args == True:
            self.check_args = False
            self.featuremap["FCAP"]["exception"]["with_args"] += 1

    def visit_Yield(self, node):
        self.featuremap["ES"]["generator"] += 1
        self.generic_visit(node)

    def visit_ListComp(self, node):
        self.featuremap["DS"]["list_comprehension"] += 1
        self.generic_visit(node)

    def visit_Assign(self, node):
        #check if a function var assigned to another var
        if hasattr(node.value, "id") and self.check_func(node.value.id, node.value.lineno):
            self.featuremap["TS"]["first_class_function"]["function_assignedto_var"] += 1
        elif type(node.value) == ast.Attribute and self.check_func(node.value.attr, node.value.lineno):
            self.featuremap["TS"]["first_class_function"]["function_assignedto_var"] += 1
        elif self.check_outside_func(node.value):          
            self.featuremap["TS"]["first_class_function"]["function_assignedto_var"] += 1
        
        #check left value
        for i in node.targets:
            if type(i) == ast.Attribute and hasattr(i.value, "id") and i.value.id == "self" and i.attr.startswith("__") and len(self.classnames) > 0 and i.attr not in self.classattrs[len(self.classattrs) - 1]:
                self.featuremap["OOP"]["encapsulation"]["private"]["var"] += 1
            elif type(i) == ast.Attribute and hasattr(i.value, "id") and i.value.id == "self" and i.attr.startswith("_") and len(self.classnames) > 0 and i.attr not in self.classattrs[len(self.classattrs) - 1]:
                self.featuremap["OOP"]["encapsulation"]["protected"]["var"] += 1

        self.generic_visit(node)


    def visit_Subscript(self, node):
        #check heterogeneous list and tuple
        if (hasattr(node.value, "id") and self.check_heterogeneous(node.value.id, node.value.lineno) == "list" 
            and hasattr(node.slice, "value") and hasattr(node.slice.value, "id")):
            self.featuremap["DS"]["heterogeneous_list"]["variable_index"] += 1
        if (hasattr(node.value, "id") and self.check_heterogeneous(node.value.id, node.value.lineno) == "list" 
            and hasattr(node.slice, "value") and hasattr(node.slice.value, "n")):
            self.featuremap["DS"]["heterogeneous_list"]["constant_index"] += 1
        if (hasattr(node.value, "id") and self.check_heterogeneous(node.value.id, node.value.lineno) == "tuple" 
            and hasattr(node.slice, "value") and hasattr(node.slice.value, "id")):
            self.featuremap["DS"]["heterogeneous_tuple"]["variable_index"] += 1
        if (hasattr(node.value, "id") and self.check_heterogeneous(node.value.id, node.value.lineno) == "tuple" 
            and hasattr(node.slice, "value") and hasattr(node.slice.value, "n")):
            self.featuremap["DS"]["heterogeneous_tuple"]["constant_index"] += 1

        self.generic_visit(node)

    def visit_Delete(self, node):
        #delete statement has reflection features
        self.featuremap["MP"]["reflection"] += 1
        self.generic_visit(node)

    def visit_Attribute(self, node):
        #some attributes have reflection features
        if node.attr in self.setup["introspection_attrs"]:
            self.featuremap["MP"]["introspection"] += 1
        self.generic_visit(node)


    def check_inheritance(self):
        #check hierarchical inheritance
        for key in self.classchildren:
            if len(self.classchildren[key]) > 1:
                self.featuremap["OOP"]["inheritance"]["hierarchical"] += 1

        #check multilevel inheritance
        classwithoutchildren = []
        for i in self.classes:
            if i not in self.classchildren:
                classwithoutchildren.append(i)

        for i in classwithoutchildren:
            for p in self.classchildren:
                if i in self.classchildren[p]:
                    for q in self.classchildren:
                        if p in self.classchildren[q]:
                            self.featuremap["OOP"]["inheritance"]["multilevel"] += 1

        #check diamond inheritance
        for i in self.classparent:
            if len(self.classparent[i]) > 1:
                parents = {}
                for p in self.classparent[i]:
                    parents[p] = self.find_parent(p)
                    parents[p].remove(p)
                found = False
                for p in parents:
                    if found:
                        break
                    for i in parents[p]:
                        if found:
                            break
                        for q in parents:
                            if i in parents[q]:
                                self.featuremap["OOP"]["inheritance"]["diamond"] += 1
                                found = True
                                break


    def find_parent(self, name):
        parents = [name]
        if name in self.classparent:
            for p in self.classparent[name]:
                parents += self.find_parent(p)
        if name == "object":
            return []
        return parents


    def finalize(self):
        self.check_inheritance()
        self.check_recursion()

    def run(self, node, html):
        #HTML Result
        self.soup = BeautifulSoup(html, features="html.parser")
        self.visit(node)
        self.finalize()

    def check_func(self, name, lineno):
        spans = self.soup.find_all(class_ ="lineno")
        if len(spans) < lineno:
            return False
        else:
            p = spans[lineno - 1].next_sibling
            while(p != None and p.name != "span"):
                if hasattr(p, "xid") and hasattr(p, "title") and p.string == name and "->" in p["title"] and "(" in p["title"] and ")" in p["title"]:
                    return True
                p = p.next_sibling
        return False

    def check_heterogeneous(self, name, lineno):
        spans = self.soup.find_all(class_ ="lineno")
        if len(spans) < lineno:
            return False
        else:
            p = spans[lineno - 1].next_sibling
            while(p != None and p.name != "span"):
                if hasattr(p, "xid") and hasattr(p, "title") and p.string == name and p["title"].startswith("[") and p["title"].endswith("]") and "|" in p["title"]:
                    types = p["title"][2:len(p["title"]) - 3].split(" | ")
                    count = 0
                    for t in types:
                        if "#" not in t and "?" not in t:
                            count += 1
                    if count > 1:
                        return "list"
                    else:
                        return False
                if hasattr(p, "xid") and hasattr(p, "title") and p.string == name and p["title"].startswith("(") and p["title"].endswith(")"):
                    res = p["title"][1: len(p["title"]) - 1]
                    types = res.split(", ")
                    for i in types:
                        for j in types:
                            if i != j and "?" not in i and "?" not in j and "#" not in i and "#" not in j:
                                return "tuple"
                p = p.next_sibling
        return False

    def check_polymorphism(self, name, lineno):
        spans = self.soup.find_all(class_ ="lineno")
        if len(spans) < lineno:
            return False
        else:
            p = spans[lineno - 1].next_sibling
            while(p != None and p.name != "span"):
                if hasattr(p, "xid") and hasattr(p, "title") and p.string == name:
                    types = p["title"].split(" / ")
                    count = 0
                    returnvalues = {}
                    for t in types:
                        if "?" not in t and " -> " in t:
                            sig = t.split(" -> ")
                            if "|" in sig[0] and "{" in sig[0] and "}" in sig[0] and "None" not in sig[0]:
                                return True
                            if sig[1] not in returnvalues and "None" not in sig[0]:
                                returnvalues[sig[1]] = sig[0]
                            elif sig[1] in returnvalues and returnvalues[sig[1]] != sig[0] and "None" not in sig[0]:
                                count += 1
                    if count > 0:
                        return True
                    else:
                        return False
                p = p.next_sibling
        return False

    def check_outside_polymorphism(self, node):
        if type(node) == ast.Name or self.lib == None:
            return False
        elif type(node) == ast.Attribute and self.lib != None:
            attrs = self.resolve_attribute(node)
            if attrs == None or (attrs[0] not in self.modules and attrs[0] not in self.modulealias.keys()):
                return False
            direct_path = "standard_libs/polymorphism_files"
            indirect_path = "standard_libs/polymorphism_files"
            for i in range(0, len(attrs) - 2):
                direct_path += "/"
                indirect_path += "/"
                direct_path += attrs[i]
                indirect_path += attrs[i]
            direct_path += "/"
            direct_path += attrs[len(attrs) - 2]
            direct_path += ".csv"
            indirect_path += ".csv"
            if  self.polys.loc[(self.polys["filepath"] == direct_path) & (self.polys["class"] == "None") & (self.polys["func"] == attrs[len(attrs) - 1])].empty == False:
                return True
            elif self.polys.loc[(self.polys["filepath"] == indirect_path) & (self.polys["class"] == attrs[len(attrs) - 2]) & (self.polys["func"] == attrs[len(attrs) - 1])].empty == False:
                return True
            else:
                return False
        return False

    def check_type(self, name, lineno):
        spans = self.soup.find_all(class_ ="lineno")
        if len(spans) < lineno:
            return None
        else:
            p = spans[lineno - 1].next_sibling
            while(p != None and p.name != "span"):
                if hasattr(p, "xid") and hasattr(p, "title") and p.string == name:
                    return p["title"]
                p = p.next_sibling
        return None

    def check_recursion(self):
        for func in self.funcsum["funcs"]:
            if self.check_recursion_interal([func], self.funcsum["funcs"][func], self.setup["recursion_limit"]) == True:
                self.featuremap["FCAP"]["recursion"] += 1
        for c in self.funcsum["classes"]:
            for func in self.funcsum["classes"][c]:
                if self.check_recursion_interal([c, func], self.funcsum["classes"][c][func], self.setup["recursion_limit"]) == True:
                    self.featuremap["FCAP"]["recursion"] += 1


    def check_recursion_interal(self, caller, callees, limit):
        if caller in callees:
            return True
        if limit < 0:
            return False
        for f in callees:
            if len(f) == 1 and f[0] in self.funcsum["funcs"]:
                return self.check_recursion_interal(caller, self.funcsum["funcs"][f[0]], limit - 1)
            elif len(f) == 2 and f[0] in self.funcsum["classes"] and f[1] in self.funcsum["classes"][f[0]]:
                return self.check_recursion_interal(caller, self.funcsum["classes"][f[0]][f[1]], limit - 1)

    def resolve_attribute(self, node):
        if type(node) == ast.Attribute:
            if type(node.value) == ast.Attribute:
                return self.resolve_attribute(node.value) + [node.attr]
            elif type(node.value) == ast.Name:
                return [node.value.id, node.attr]
            else:
                return [None, node.attr]

    def check_outside_func(self, node):
        if type(node) == ast.Name or self.lib == None:
            return False
        elif type(node) == ast.Attribute and self.lib != None:
            attrs = self.resolve_attribute(node)
            if attrs == None or (attrs[0] not in self.modules and attrs[0] not in self.modulealias.keys()):
                return False
            direct_path = "standard_libs/funcs"
            indirect_path = "standard_libs/funcs"
            for i in range(0, len(attrs) - 2):
                direct_path += "/"
                indirect_path += "/"
                direct_path += attrs[i]
                indirect_path += attrs[i]
            direct_path += "/"
            direct_path += attrs[len(attrs) - 2]
            direct_path += ".csv"
            indirect_path += ".csv"
            if  self.polys.loc[(self.polys["filepath"] == direct_path) & (self.polys["class"] == "None") & (self.polys["func"] == attrs[len(attrs) - 1])].empty == False:
                return True
            elif self.polys.loc[(self.polys["filepath"] == indirect_path) & (self.polys["class"] == attrs[len(attrs) - 2]) & (self.polys["func"] == attrs[len(attrs) - 1])].empty == False:
                return True
            else:
                return False
        return False

    def standard_print(self, sort = False):
        table = PrettyTable(["Category Number", "Language Feature", "Nums of Appearance"])
        table.align["Language Feature"] = 'l'
        table.sortby = "Category Number"
        if sort:
            table.sortby = "Nums of Appearance"
            table.reversesort = True
        else:
            table.add_row(["1", "Function Call and Argument Passing", "----------"])
            table.add_row(["2", "Type System", "----------"])
            table.add_row(["3", "Evaluation Strategy", "----------"])
            table.add_row(["4", "Object-oriented Programming", "----------"])
            table.add_row(["5", "Data Structure", "----------"])
            table.add_row(["6", "MetaProgramming", "----------"])
        table.add_row(["1.1", "Keyword-only Parameter", self.featuremap["FCAP"]["kwonlyargs"]])
        table.add_row(["1.2", "Keyword Parameter", self.featuremap["FCAP"]["kwarg"]])
        table.add_row(["1.3", "Position-only Parameter", self.featuremap["FCAP"]["posonlyargs"]])
        table.add_row(["1.4", "Multiple Return", self.featuremap["FCAP"]["multiple_return"]])
        #table.add_row(["1.4", "Loop", ""])
        table.add_row(["1.5.1", "Loop - While Statement", self.featuremap["FCAP"]["loop"]["while"]])
        table.add_row(["1.5.2", "Loop - For Statement", self.featuremap["FCAP"]["loop"]["for"]])
        table.add_row(["1.5.3", "Loop - Continue Statement", self.featuremap["FCAP"]["loop"]["continue"]])
        table.add_row(["1.5.4", "Loop - Break Statement", self.featuremap["FCAP"]["loop"]["break"]])
        table.add_row(["1.6", "Recursion", self.featuremap["FCAP"]["recursion"]])
        table.add_row(["1.7", "Nested Function", self.featuremap["FCAP"]["nested_function"]])
        #table.add_row(["1.7", "Exception", ""])
        table.add_row(["1.8.1", "Exception - Try Statement", self.featuremap["FCAP"]["exception"]["try"]])
        table.add_row(["1.8.2", "Exception - Raise Statement", self.featuremap["FCAP"]["exception"]["raise"]])
        table.add_row(["1.8.3", "Exception - Exceptions with Variable Arguments", self.featuremap["FCAP"]["exception"]["with_args"]])
        #table.add_row(["1.8", "Packing and Unpacking arguments", ""])
        table.add_row(["1.9.1", "Packing Arguments", self.featuremap["FCAP"]["packing_and_unpacking"]["packing"]])
        table.add_row(["1.9.2", "Unpacking Arguments", self.featuremap["FCAP"]["packing_and_unpacking"]["unpacking"]])
        table.add_row(["1.10", "Decorator", self.featuremap["FCAP"]["decorator"]])
        #table.add_row(["2.1", "First Class Function", ""])
        table.add_row(["2.1.1", "First Class Function - As Parameter", self.featuremap["TS"]["first_class_function"]["function_as_parameter"]])
        table.add_row(["2.1.2", "First Class Function - As Return Value", self.featuremap["TS"]["first_class_function"]["function_as_returnvalue"]])
        table.add_row(["2.1.3", "First Class Function - Assigned to Variables", self.featuremap["TS"]["first_class_function"]["function_assignedto_var"]])
        table.add_row(["2.2", "Gradual Typing", self.featuremap["TS"]["gradual_typing"]])
        table.add_row(["3.1", "Generator", self.featuremap["ES"]["generator"]])
        table.add_row(["4.1.1", "Inheritance - Single Inheritance", self.featuremap["OOP"]["inheritance"]["single"]])
        table.add_row(["4.1.2", "Inheritance - Multiple Inheritance", self.featuremap["OOP"]["inheritance"]["multiple"]])
        table.add_row(["4.1.3", "Inheritance - Hierarchical Inheritance", self.featuremap["OOP"]["inheritance"]["hierarchical"]])
        table.add_row(["4.1.4", "Inheritance - Multilevel Inheritance", self.featuremap["OOP"]["inheritance"]["multilevel"]])
        table.add_row(["4.1.5", "Inheritance - Diamond Inheritance", self.featuremap["OOP"]["inheritance"]["diamond"]])
        table.add_row(["4.2.1", "Encapsulation - Protected Methods", self.featuremap["OOP"]["encapsulation"]["protected"]["method"]])
        table.add_row(["4.2.2", "Encapsulation - Protected Attributes", self.featuremap["OOP"]["encapsulation"]["protected"]["var"]])
        table.add_row(["4.2.3", "Encapsulation - Private Methods", self.featuremap["OOP"]["encapsulation"]["private"]["method"]])
        table.add_row(["4.2.4", "Encapsulation - Private Attributes", self.featuremap["OOP"]["encapsulation"]["private"]["var"]])
        table.add_row(["4.3", "Nested Class", self.featuremap["OOP"]["nested_class"]])
        table.add_row(["4.4", "Parametic Polymorphism", self.featuremap["OOP"]["polymorphism"]["parametic"]])
        table.add_row(["5.1", "List Comprehension", self.featuremap["DS"]["list_comprehension"]])
        table.add_row(["5.2.1", "Heterogeneous List - Constant Index", self.featuremap["DS"]["heterogeneous_list"]["constant_index"]])
        table.add_row(["5.2.2", "Heterogeneous List - Variable Index", self.featuremap["DS"]["heterogeneous_list"]["variable_index"]])
        table.add_row(["5.3.1", "Heterogeneous Tuple - Constant Index", self.featuremap["DS"]["heterogeneous_tuple"]["constant_index"]])
        table.add_row(["5.3.2", "Heterogeneous Tuple - Variable Index", self.featuremap["DS"]["heterogeneous_tuple"]["variable_index"]])
        table.add_row(["6.1", "Introspection", self.featuremap["MP"]["introspection"]])
        table.add_row(["6.2", "Reflection", self.featuremap["MP"]["reflection"]])
        table.add_row(["6.3", "Metaclass", self.featuremap["MP"]["metaclass"]])

        print(table)

    def print_tocsv(self, csvfile, sourcefile):
        keys = ["filepath"]
        values = [sourcefile]
        for cat in self.featuremap:
            for f in self.featuremap[cat]:
                if isinstance(self.featuremap[cat][f], dict):
                    for i in self.featuremap[cat][f]:
                        if isinstance(self.featuremap[cat][f][i], dict):
                            for j in self.featuremap[cat][f][i]:
                                keys.append(cat+f+i+j)
                                values.append(self.featuremap[cat][f][i][j])
                        else:
                            keys.append(cat+f+i)
                            values.append(self.featuremap[cat][f][i])
                else:
                    keys.append(cat+f)
                    values.append(self.featuremap[cat][f])
    

        if os.path.exists(csvfile):
            newdict = {}
            for i in range(0, len(keys)):
                newdict[keys[i]] = values[i]
            df = pd.read_csv(csvfile, header=None, names = keys, sep = ",")
            df = df.append(newdict, ignore_index = True)
            df.to_csv(csvfile, index = False, header = False)

        else:
            newdict = {}
            for i in range(0, len(keys)):
                newdict[keys[i]] = [values[i]]
            df = pd.DataFrame(newdict)
            df.to_csv(csvfile, index = False, header = True)
#@profile
#@time_out(600, timeout_callback)
def main():
    sourcefile = None
    htmlfile = None
    showast = False
    sort = False
    setup = {}
    csv = False
    csvfile = None
    lib = None
    cfg_file = None
    try:
        opts, args = getopt.getopt(sys.argv[1:],"-h-s:-t:-a-m-c:-l:-f:",["source=","typeres=", "ast", "most-frequently", "csvfile=", "standard-libs=", "configfile="])
    except getopt.GetoptError:
        print("Unsupportable arguments, please see featureScanner.py -h")
        sys.exit(-1)
    for opt, arg in opts:
        if opt == '-h':
            print("Usage:\n-s/--source <Python Source File> : Indicate the path of Python source file")
            print("-t/--typeres <Type Inference Result File> : Indicate the path of type inference result file")
            print("-a/--ast : Show the AST of source code")
            print("-m/--most-frequently : Sort the results and show language features which used most frequenly")
            print("-c/--csvfile <CSV File> : Write the result into the csv file")
            print("-l/--standard-libs <Standard Libs Info Directiry Path> : Indicate the info directory of standard libs to help conduct accurate cognition")
            sys.exit()
        elif opt in ("-s", "--source"):
            sourcefile = arg
        elif opt in ("-t", "--typeres"):
            htmlfile = arg
        elif opt in ("-a", "--ast"):
            showast = True
        elif opt in ("-m", "--most-frequently"):
            sort = True
        elif opt in ("-c", "--csvfile"):
            csv = True
            csvfile = arg
        elif opt in ("-l", "--standard-libs"):
            lib = arg
        elif opt in ("-f", "--configfile"):
            cfg_file = arg
      
    if sourcefile != None and htmlfile != None and cfg_file != None:
        
        #set config
        config = configparser.ConfigParser()
        config.read(cfg_file)
        if "scanner_defaults" not in config.keys():
            print("Error: Can not read config file!")
            exit(-1)
        for key in config["scanner_defaults"]:
            setup[key] = config["scanner_defaults"][key]
        visitor = analyzer(setup, lib)
        source = open(sourcefile, "r").read()
        root = ast.parse(source)
        if showast == True:
            astpretty.pprint(root, indent = '    ')
        visitor.run(root, open(htmlfile, "r"))
        if csv == True and csvfile != None:
            visitor.print_tocsv(csvfile, sourcefile)
        else:
            visitor.standard_print(sort)
    else:
        print("Error: Python source file or type inference result file or config file missing!")


if __name__ == "__main__":
    main()
    




