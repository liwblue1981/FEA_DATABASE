# from common.local_settings import local_settings
# import pymysql
# # import matplotlib.pyplot as plt
# # import math
# # from matplotlib.ticker import (MultipleLocator, FormatStrFormatter, AutoMinorLocator)
#
# try:
#     db = pymysql.Connect(
#         # host='10.131.12.156',
#         host='cdcpillx191',
#         user='liw00073',
#         password='liw00073',
#         database='FEADataBase'
#     )
# except Exception as e:
#     print (e)

# # db = pymysql.connect('10.218.32.245', 'root', 'root', 'fm_projects')
# cursor = db.cursor()
# cursor.execute('select beadid, preaload_Percentage, myData from tfatigue where name="FB-3000W-310H-200T-0R-0L-0preLoad-0SW-NonT-FMGS1"')
#
# data = cursor.fetchone()
# #
# temp=data[1].split(',')
# pre_load_list=[]
# for val in temp:
#     pre_load_list.append(float(val))
#
# temp_load=[]
# temp_value=[]
# temp=data[2].split('\r\n')
# for temp_data in temp:
#     current_line = temp_data.split(',')
#     for i, each_data in enumerate(current_line):
#         if i==0:
#             temp_load.append(float(each_data))
#             temp_value.append([])
#         else:
#             temp_value[-1].append(float(each_data))
#
# print(temp_load)
# print(temp_value)
# db.close()

import os
import stat
import paramiko
import traceback

'''
使用paramiko类实现ssh的连接登陆,以及远程文件的上传与下载, 基本远程命令的实现等

'''

#
# from lib import local_function
#
# if __name__ == "__main__":
#     ssh = local_function.SSH(ip='shnhcnlx036', username='liw00073', password='python111')  # 创建一个ssh类对象
#     # ssh = SSH(ip='shnhcnlx036', username='liw00073', password='python111')  # 创建一个ssh类对象
#     ssh.connect()  # 连接远程服务器
#     cmd = 'ls -lh'
#     ssh.execute_cmd(cmd)  # 执行命令
#     remotefile, local_file = '/data/Kevin/FEA19-0840/gasket-FEA19-0840-test.inp', 'D:/Programming/chg_readin/download.inp'
#     ssh._sftp_get(remotefile, local_file)  # 下载文件
#     remotefile, local_file = '/data/Kevin/FEA19-0840/FEA19-0840_chg_postprocess_header.py', 'D:/Programming/chg_readin/FEA19-0840_chg_postprocess_header.py'
#     ssh._sftp_put(local_file, remotefile)  # 上传文件夹
#     ssh.close()

def test_print(**kwargs):
    print(kwargs['aaa'])

num = {'aaa':'try this'}
test_print(**num)