
Instructions:

1. Run server1.py, server2.py, server3.py, server4.py at the same time

2. Edit configuration.txt under folder balancer, the format for each server MUST be host:port, and must be 1 line for each server

3. Run balancer.py

4. Run client.py with argument of the details of the balancer, it MUST be in the form of http://host:port/filename


Additionaly information:

For testing purposes, a large image file is set as the default test file for the balancer to test the performance of each server, the file name is test.jpg

Also there are a few extra jpg and txt files under server directory, feel free to use them for testing or deleting them. 


Xiaoyu Xie
Dec 9th, 2020
