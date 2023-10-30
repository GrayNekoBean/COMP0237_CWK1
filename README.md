# COMP0237_CWK1
Sync our work here.

## How to run repair.py

* Make sure pytest is installed
* **No need to specify the project path in the command line. The project path will always be "repairs/" to make sure the program functions properly**

### Use config file to specify the target program
Use the following command to run repair.py with config file:
```
python repair.py --config [config_file_path]
```
For example:
```
python repair.py --config ./lis-python.pyggi.config
```

### Use Target argument to specify the target program
Use the following command to run repair.py with target argument:
```
python repair.py --target [target_bug]-[target_program]
```

For example:
```
python repair.py --target lis-python
```

When there's no config file for the target, the program will automatically generate a config file for the target and run the program with the config file generated.

> ⚠️ **Warning**: Auto Generation for Java programs is not supported yet. I will add this feature very soon.

## How to test more programs

* Follow the instructions above, use the ***target*** argument to specify or generate a config file for the target program. Try run this command on more bugs in QuixBugs to test them.

* If you want to test more programs with your own config file, place your config file in the "repairs/" folder and use the ***config*** argument to specify the config file.

* To make the result output to a file at the same time, use `tee` command (in Linux, not sure in Mac):
```
python repair.py --target [target_bug]-[target_program] | tee [output_file_path]
```

For example:
```
python repair.py --target lis-python | tee ./lis-python-result.txt
```

But please note that the Log (non-result part) will always be printed on console and saved in the log file under `.pyggi/logs/` folder, this is done by PyGGI itself. And the result will not include the Log part


> Also, Please Remember to clean up your `.pyggi/tmp_variants` directory periodically, otherwise it will take up a lot of space on your computer.