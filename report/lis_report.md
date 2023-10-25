# PYGGI QuixBugs Repairing Report - LIS

## Program Description

Finding LIS is a classic problem in computer science. The problem is to find the longest subsequence of a given sequence such that all elements of the subsequence are sorted in increasing order. 

The program is implemented in both Java and Python. The Python version uses a dynamic programming approach to solve the problem. The Java version is a direct translation of the Python version.

## Bug Description

Take Python version as an example. The bug in lis function is on line 14. The problem code is:

```python
    longest = length + 1
```

And the correct code should be:

```python
    longest = max(length + 1, longest)
```

Since the ***if*** statement has an two condition connected by OR operator, the program will execute the code on line 14 on either condition is true. However, only in the first condition `length == longest` should make the `longest` variable been assigned a new value, because only this situation means a longer subsequence is found. In the second condition, the `longest` variable should not be increased, only the value in the `ends` dictionary should be updated.

This code is approximately equal to:

```python
    if length == longest or val < arr[ends[length]]:
        ends[length + 1] = i
        if length == longest:
            longest = length + 1
```

The bug is that the `longest` variable is increased in the second condition, which is not correct.

## The Repairing Process

By using our script repair.py with following arguments:

```bash
python repair.py --target lis-python --mode tree --epoch 10 --iter 100
```

It tooks about 5 minutes to run the script on my laptop. In epoch, once the right solution is been found, it will jump to the next epoch. So the iteration number is not the actual number of iteration.

## Analysis of the Patches

In the tree mode, we can get two repaired patches from the result that could pass all the tests in QuixBugs. Both fix are correct, but it makes the code less readable and redundant, The PYGGI changes the code in a rough way and coincidentally corrected the code logic.

The first patch is:

```diff
Diff: 
*** before: QuixBugs/python_programs/lis.py
--- after: QuixBugs/python_programs/lis.py
***************
*** 5,10 ****
--- 5,11 ----
          prefix_lengths = [j for j in range(1, longest + 1) if arr[ends[j]] < val]
          length = max(prefix_lengths) if prefix_lengths else 0
+         ends[length + 1] = i
          if length == longest or val < arr[ends[length + 1]]:
              ends[length + 1] = i
              longest = length + 1

```

The original code actually has a redundant condition in the if statement, the second condition `val < arr[ends[length + 1]]` is always true, because when calculating the `prefix_lengths`, the code has ensured that the value of `val` is always greater than `arr[ends[j]]`, and smaller than `arr[ends[j + 1]]`.

In this trick, the `ends[length + 1] = i` is moved out of the if statement. And makes the condition `val < arr[ends[length + 1]]` always false. Then only when length == longest, the `longest` variable will be updated, and the `ends` dictionary will be updated but with a same value which makes no difference.

The code is then equivalent to:

```python
        prefix_lengths = [j for j in range(1, longest + 1) if arr[ends[j]] < val]
        length = max(prefix_lengths) if prefix_lengths else 0
        ends[length + 1] = i
        if length == longest:
            longest = length + 1
```

The second patch is:

```diff
Diff: 
*** before: QuixBugs/python_programs/lis.py
--- after: QuixBugs/python_programs/lis.py
***************
*** 7,13 ****
          length = max(prefix_lengths) if prefix_lengths else 0
          if length == longest or val < arr[ends[length + 1]]:
              ends[length + 1] = i
!             longest = length + 1
      return longest
  
  
--- 7,15 ----
          length = max(prefix_lengths) if prefix_lengths else 0
          if length == longest or val < arr[ends[length + 1]]:
              ends[length + 1] = i
!             if length == longest or val < arr[ends[length + 1]]:
!                 ends[length + 1] = i
!                 longest = length + 1
      return longest
```

This one uses another trick. Since the arr[ends[length + 1]] is now been updated in the first enter of the if statement, this condition on the second if statement will always be false. So the condition in the second if collapsed to `length == longest`, also the second time running this line `ends[length+1] = i` makes no diffence to any variable from the first running. So this code is equivalent to:

```python
if length == longest or val < arr[ends[length + 1]]:
    ends[length + 1] = i
    if length == longest:
        longest = length + 1
```

which is also a correct logic for this code.

