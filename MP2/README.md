# MP2 说明文档
作者：袁小迪（2019012382）

## 文件目录

- MP2: 根目录
    - README.md: MP2 说明文档
    - MP2.py: 源代码（Python）
    - MP2.log: 源代码执行输出
    - screenshots: 运行截图文件夹
        - screenshots1~4.jepg 源代码执行输出的截图，内容同MP2.log

## 说明

### 运行环境：

Ubuntu，SQL Server Press。

### 特性：

尽可能使用了 SQL 实现大部分功能（而不是依赖 Python）。使用了 Trigger、Constraint 等最大程度地简化操作，详见 ConnectDatabase() 函数。

### Screenshot：

使用的 Python 库为 pyodbc。因为没有安装 SQL Server 的图形界面，所以 screenshot 截的是命令行中的运行结果。

对程序的测试分为5部分（5个 Stage），每一个 Stage 测试程序的某几个函数，测试的设计尽可能涉及了所有的合法情况和不合法情况。输出内容已存储在 MP2.log 文件中。每一次对数据库的修改操作都会在 MP2.log 文件中留下以 "[Operation Log]" 开头的一条记录。另外，每个 Stage 中会打印一次至多次该操作涉及到的完整表格，以证明程序运行的正确性。5个 Stage 共同覆盖了所有的13个函数。



