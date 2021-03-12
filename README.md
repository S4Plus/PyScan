# PyScan

This project is a Python language feature scanning tool proposed in paper: **An Empirical Study For Common Language Features Used in Python Projects**. This tool is developed by [Yun Peng](https://www.yunpeng.work) under the guidance of Prof. [Yu Zhang](http://staff.ustc.edu.cn/~yuzhang) in the [S4Plus](https://s4plus.ustc.edu.cn/) team at [USTC](https://www.ustc.edu.cn/).

This tool aims to scan the occurrences of 22 Python language features for a single Python source code file or a Python project.

If you use PyScan in your research, please cite our paper as follows:

```
@inproceedings{ peng2021pyscan,
    title	= {An Empirical Study for Common Language Features Used in Python Projects},
    author	= {Peng, Yun and Zhang, Yu and Hu, Mingzhe},
    booktitle={Proceedings of 2021 28th IEEE International Conference on Software Analysis, Evolution and Reengineering},
	month	= {March},
    year	={2021},
    organization={IEEE},
    doi		= {},
    url		= {},
}
```

## Language Feature

PyScan scans the following language features, for the explanations and definitions of each language feature, please check our paper.

|          Category           |        Language Feature        |
| :-------------------------: | :----------------------------: |
|          Function           |        Keyword Argument        |
|          Function           |     Keyword-only Argument      |
|          Function           |     Position-only Argument     |
|          Function           |        Multiple Return         |
|          Function           | Packing and Unpacking Argument |
|          Function           |           Decorator            |
|          Function           |           Exception            |
|          Function           |           Recursion            |
|          Function           |        Nested Function         |
|         Type System         |      First-class Function      |
|         Type System         |         Gradual Typing         |
| Loop & Evaluation Strategy  |              Loop              |
| Loop & Evaluation Strategy  |           Generator            |
| Object-Oriented Programming |          Inheritance           |
| Object-Oriented Programming |          Polymorphism          |
| Object-Oriented Programming |         Encapsulation          |
| Object-Oriented Programming |          Nested Class          |
|       Data Structure        |       List Comprehension       |
|       Data Structure        |  Heterogeneous List and Tuple  |
|       MetaProgramming       |         Introspection          |
|       MetaProgramming       |           Reflection           |
|       MetaProgramming       |           Metaclass            |

##Usage

First you need to install all packages Pyscan need:

```sh
pip install -r requirements.txt
```

Before using PyScan, you may first need to use [Pysonar2](https://github.com/yinwang0/pysonar2) to generate type inference result file for the target source file.

The usage of PyScan:

```python
-s/--source <Python Source File> : Indicate the path of Python source file
-t/--typeres <Type Inference Result File> : Indicate the path of type inference result file
-a/--ast : Show the AST of source code
-m/--most-frequently : Sort the results and show language features which used most frequenly
-c/--csvfile <CSV File> : Write the result into the csv file
-l/--standard-libs <Standard Libs Info Directiry Path> : Indicate the info directory of standard libs to help conduct accurate cognition
```

**Required Enviroment:** Python 3.8.2 or higher

Please note that`-s` ,`-t`, `-l`, `-f`  are required in order to complete the entire scanning process. 

**Example:**

```bash
python3 featurescanner.py -s <sourcefile> -t <typeinference file> -f config.ini -l standard_res
```

If you want to analyze the whole project repo, try to use `analyze_project.sh`:

```
bash analyze_project.sh <Path to source file repo> <Path of Pysonar2 runtime file>
```

The Pysonar2 runtime file is like this:

```
target/pysonar-<version>.jar
```

##License

PyScan is liscensed under the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).