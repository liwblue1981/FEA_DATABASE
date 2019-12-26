import pymysql
import matplotlib.pyplot as plt
import math
from matplotlib.ticker import (MultipleLocator, FormatStrFormatter, AutoMinorLocator)
from common.local_settings import local_settings
import os
import stat
import paramiko
import traceback
import time


class SSH:
    def __init__(self, ip, port=22, username=None, password=None, timeout=30):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        # paramiko.SSHClient() 创建一个ssh对象，用于ssh登录以及执行操作
        self.ssh = paramiko.SSHClient()
        # paramiko.Transport()创建一个文件传输对象，用于实现文件的传输
        self.t = paramiko.Transport(sock=(self.ip, self.port))

    def _password_connect(self):
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname=self.ip, port=22, username=self.username, password=self.password)
        self.t.connect(username=self.username, password=self.password)  # sftp 远程传输的连接

    def _key_connect(self):
        # 获取本地的私钥文件 一般是在 ~/.ssh/id_rsa
        self.pkey = paramiko.RSAKey.from_private_key_file('/home/liw00073/.ssh/authorized_keys', )
        # self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname=self.ip, port=22, username=self.username, pkey=self.pkey)
        # 建立文件传输的连接
        self.t.connect(username=self.username, pkey=self.pkey)

    def connect(self):
        # 这里我只使用用户名和密码进行连接
        try:
            self._password_connect()
        except:
            print('ssh password connect failed!')
        # try:
        #     self._key_connect()
        # except:
        #     print('ssh key connect failed, trying to password connect...')
        #     try:
        #         self._password_connect()
        #     except:
        #         print('ssh password connect faild!')

    def close(self):
        self.t.close()
        self.ssh.close()

    def execute_cmd(self, cmd):
        stdin, stdout, stderr = self.ssh.exec_command(cmd)

        res, err = stdout.read(), stderr.read()
        result = res if res else err

        return result.decode()

    # 从远程服务器获取文件到本地
    def _sftp_get(self, remotefile, localfile):
        sftp = paramiko.SFTPClient.from_transport(self.t)
        sftp.get(remotefile, localfile)

    # 从本地上传文件到远程服务器
    def _sftp_put(self, localfile, remotefile):
        sftp = paramiko.SFTPClient.from_transport(self.t)
        sftp.put(localfile, remotefile)

    # 递归遍历远程服务器指定目录下的所有文件
    def _get_all_files_in_remote_dir(self, sftp, remote_dir):
        all_files = list()
        if remote_dir[-1] == '/':
            remote_dir = remote_dir[0:-1]

        files = sftp.listdir_attr(remote_dir)
        for file in files:
            filename = remote_dir + '/' + file.filename

            if stat.S_ISDIR(file.st_mode):  # 如果是文件夹的话递归处理
                all_files.extend(self._get_all_files_in_remote_dir(sftp, filename))
            else:
                all_files.append(filename)

        return all_files

    def sftp_get_dir(self, remote_dir, local_dir):
        try:

            sftp = paramiko.SFTPClient.from_transport(self.t)

            all_files = self._get_all_files_in_remote_dir(sftp, remote_dir)

            for file in all_files:

                local_filename = file.replace(remote_dir, local_dir)
                local_filepath = os.path.dirname(local_filename)

                if not os.path.exists(local_filepath):
                    os.makedirs(local_filepath)

                sftp.get(file, local_filename)
        except:
            print('ssh get dir from master failed.')
            print(traceback.format_exc())

    # 递归遍历本地服务器指定目录下的所有文件
    def _get_all_files_in_local_dir(self, local_dir):
        all_files = list()

        for root, dirs, files in os.walk(local_dir, topdown=True):
            for file in files:
                filename = os.path.join(root, file)
                all_files.append(filename)

        return all_files

    def sftp_put_dir(self, local_dir, remote_dir):
        try:
            sftp = paramiko.SFTPClient.from_transport(self.t)

            if remote_dir[-1] == "/":
                remote_dir = remote_dir[0:-1]

            all_files = self._get_all_files_in_local_dir(local_dir)
            for file in all_files:

                remote_filename = file.replace(local_dir, remote_dir)
                remote_path = os.path.dirname(remote_filename)

                try:
                    sftp.stat(remote_path)
                except:
                    # os.popen('mkdir -p %s' % remote_path)
                    self.execute_cmd('mkdir -p %s' % remote_path)  # 使用这个远程执行命令

                sftp.put(file, remote_filename)

        except:
            print('ssh get dir from master failed.')
            print(traceback.format_exc())


class ProcessStatus:
    def __init__(self, num=0, text='Start_Now'):
        self.num_progress = num
        self.text_progress = text
        self.dict = {
            'num_progress': self.num_progress,
            'text_progress': self.text_progress,
        }
        self.record = []
        self.archive_path = ''

    def get_status(self):
        self.dict = {
            'num_progress': self.num_progress,
            'text_progress': self.text_progress,
        }
        return self.dict

    def set_archive_path(self, path):
        self.archive_path = path
        with open(self.archive_path, 'wt', encoding='utf-8') as f:
            pass

    def get_archive_path(self):
        return self.archive_path

    def set_status(self, num, text):
        self.num_progress = num
        self.text_progress = text

    def add_record(self, arr):
        arr.insert(0, time.strftime("%X", time.localtime()))
        self.record.append(arr)
        # self.record_write()

    def record_write(self):
        with open(self.archive_path, 'at', encoding='utf-8') as f:
            for item in self.record:
                f.write(str(item[0]).ljust(30) + str(item[1]).ljust(50) + str(item[2]).ljust(30) + '\n')

    def __str__(self):
        return str(self.record)


global process_bar_read
global process_bar_process
process_bar_read = ProcessStatus()
process_bar_process = ProcessStatus()


def read_log_from_server(server_name, server_location, process_bar):
    """
    读取整个运行Python的过程,返回给前端,显示在状态栏上.只有当状态发生更新的时候,才会请求读取.
    :param hostname: 服务器名称
    :return: 返回状态码,包括进度比例和当前运行状态
    """
    log_file = process_bar_process.get_archive_path()
    folder_name = log_file.rsplit('/', 1)[0]
    file_name = log_file.rsplit('/', 1)[1]
    remote_folder = server_location
    try:
        # 下载日志文件
        res = connect_to_server(server_name, process_bar_process, 10, 'Read Log File', [file_name], remote_folder,
                                folder_name)
        if res:
            with open(log_file, 'rt', encoding='utf-8') as f:
                line = f.readlines()[-1].split()
                # 这里反一反, 将状态进度放在最后, 文本信息放在中间
                num_value = line[2].strip()
                text_value = line[1].strip()
                if not num_value.isdigit():
                    num_value = 10
                    text_value = 'Waiting to Start Abaqus Viewer'
    except Exception as e:
        num_value = 0
        text_value = str(e)
    process_bar.set_status(num_value, text_value)
    return process_bar.get_status()


def connect_to_server(hostname, process_bar, num_value, text_value, file_list, remote_folder, local_folder,
                      down_up='Download'):
    username = local_settings['USER_NAME']
    password = local_settings['PASSWORD']
    # 4. 尝试建立链接
    try:
        connect_server = SSH(ip=local_settings[hostname], username=username, password=password)
        connect_server.connect()
        process_bar.set_status(num_value, text_value)
        process_bar.add_record([text_value, ' Successfully'])
    except Exception as e:
        process_bar.set_status(num_value, text_value)
        process_bar.add_record([text_value, 'Failed'])
        process_bar.add_record(['*' * 10 + 'Error', str(e)])
        return False
    # 5. 尝试下载文件
    try:
        for temp_file in file_list:
            remote_file = os.path.join(remote_folder, temp_file)
            local_file = os.path.join(local_folder, temp_file)
            if down_up == 'Download':
                connect_server._sftp_get(remote_file, local_file)
                text_value = temp_file + ' Download'
            elif down_up == 'Upload':
                connect_server._sftp_put(local_file, remote_file)
                text_value = temp_file + ' Upload'
            process_bar.add_record([text_value, 'Finished'])
        process_bar.set_status(num_value + 5, down_up + ' Done')
        connect_server.close()
    except Exception as e:
        text_value = 'Failed to Download Required Files!'
        process_bar.set_status(num_value + 5, text_value)
        process_bar.add_record(['Files ' + str(temp_file), 'Failed'])
        process_bar.add_record(['*' * 10 + 'Error', str(e)])
        return False
    return True


def connect_fatigue_database(gasket_section):
    # gasket_section[elem_set_name] = [behavior_set_name, gap_value, 0]
    database_info = local_settings['fatigue_server']
    try:
        db = pymysql.Connect(
            host=database_info['host'],
            user=database_info['user'],
            password=database_info['password'],
            database=database_info['database'],
        )
        process_bar_read.add_record(['Connect to fatigue_server', 'Succeed'])
    except Exception as e:
        process_bar_read.add_record(['Connect to fatigue_server', 'Failed'])
        process_bar_read.add_record(['*' * 10 + 'Error', str(e)])

    cursor = db.cursor()
    failed_set = []
    try:
        for elem_set_name in gasket_section:
            behavior_set_name = gasket_section[elem_set_name][0].rsplit('-', 3)[0]
            fatigue_id = gasket_section[elem_set_name][2]
            if not fatigue_id:
                cursor.execute('select beadid, preaload_Percentage, myData from ' + database_info[
                'fatigue_table'] + ' where name=\'' + behavior_set_name + '\'')
            else:
                cursor.execute('select beadid, preaload_Percentage, myData from ' + database_info[
                    'fatigue_table'] + ' where beadid=' + str(fatigue_id))
            data = cursor.fetchone()
            if data:
                gasket_section[elem_set_name][2] = data[0]
                temp = data[1].split(',')
                pre_load_list = []
                for val in temp:
                    pre_load_list.append(float(val))
                temp_load = []
                temp_value = []
                temp = data[2].split('\r\n')
                for temp_data in temp:
                    current_line = temp_data.split(',')
                    for i, each_data in enumerate(current_line):
                        if i == 0:
                            temp_load.append(float(each_data))
                            temp_value.append([])
                        else:
                            temp_value[-1].append(float(each_data))
                gasket_section[elem_set_name].append([pre_load_list, temp_load, temp_value])
            else:
                failed_set.append(elem_set_name)
    except Exception as e:
        process_bar_read.add_record(['Connect to Fatigue Table', 'Failed'])
        process_bar_read.add_record(['*' * 10 + 'Error', str(e)])
    finally:
        db.close()
    return gasket_section, failed_set


def connect_request_database(fea_number):
    database_info = local_settings['request_server']
    try:
        db = pymysql.Connect(
            host=database_info['host'],
            user=database_info['user'],
            password=database_info['password'],
            database=database_info['database'],
        )
        process_bar_read.add_record(['Connect to request_server', 'Succeed'])
        cursor = db.cursor()
        try:
            cursor.execute(
                'select * from ' + database_info['request_table'] + ' where request_number=\'' + fea_number + '\'')
            data = cursor.fetchone()
            res = {
                'request_number': fea_number,
                'title': data[2],
                'customer': data[3],
                'project_id': data[4],
                'submit_login': data[0],
                'analyst_login': data[17],
            }
        except Exception as e:
            process_bar_read.add_record(['Connect to request_table', 'Failed'])
            process_bar_read.add_record(['*' * 10 + 'Error', str(e)])

        try:
            cursor.execute('select * from ' + database_info['project_table'] + ' where project_id=' + res['project_id'])
            data = cursor.fetchone()
            res['project_name'] = data[3]
        except Exception as e:
            process_bar_read.add_record(['Connect to project_table', 'Failed'])
            process_bar_read.add_record(['*' * 10 + 'Error', str(e)])

        try:
            cursor.execute(
                'select * from ' + database_info['user_table'] + ' where login=\'' + res['submit_login'] + '\'')
            data = cursor.fetchone()
            res['submit_name'] = data[2]
            cursor.execute(
                'select * from ' + database_info['user_table'] + ' where login=\'' + res['analyst_login'] + '\'')
            data = cursor.fetchone()
            res['analyst_name'] = data[2]
        except Exception as e:
            process_bar_read.add_record(['Connect to project_table', 'Failed'])
            process_bar_read.add_record(['*' * 10 + 'Error', str(e)])
    except Exception as e:
        process_bar_read.add_record(['Connect to Host', 'Failed'])
        process_bar_read.add_record(['*' * 10 + 'Error', str(e)])
    finally:
        db.close()

    return res


def read_main_file(remote_file):
    step_definition = []
    para_definition = {}
    key_para = {
        'bolt_node': '',
        'relative_motion': 'NO',
        'bolt_force': 0,
        'ini_assem': 0,
        'hot_assem': 0,
        'p_dome': 0,
    }
    process_bar_read.add_record(['**' + 'Read Main Input File' + '**', ' Start'])
    with open(remote_file, 'rt', encoding='utf-8') as f:
        while True:
            line = f.readline().strip().upper()
            if line:
                # 参数定义只在开头读取一次,后续如果有定义,会被忽略
                if not para_definition:
                    # 开始定义参数
                    if line.startswith('*PARAMETER'):
                        while True:
                            line = f.readline().strip().upper()
                            if not line.startswith('**'):
                                # 只有一个*,表示定义参数完毕,已经进入下一行命令
                                if line.startswith('*'):
                                    process_bar_read.add_record(['Read_Parameters', 'Succeed'])
                                    break
                                else:
                                    # 参数定义格式: F_pre_bolt=84000
                                    temp = line.split('=')
                                    para_definition[temp[0]] = temp[1]
                # 读取载荷步信息,把所有*STEP和*END STEP之间的内容,刨去注释,全部读入.
                process_bar_read.set_status(17, 'Finished Reading Parameters')
                if line.startswith('*STEP'):
                    step_definition.append([])
                    while True:
                        line = line.strip().upper()
                        # 不要把注释语句输入
                        if not line.startswith('**'):
                            step_definition[-1].append(line)
                        line = f.readline().strip()
                        if '*END STEP' == line:
                            step_definition[-1].append(line)
                            # process_bar_read.add_record(['Read_Steps', str(len(step_definition))])
                            break
            else:
                process_bar_read.set_status(18, 'Finished Reading Steps')
                break
    # 查找螺栓节点集合名称
    step = step_definition[0]
    for j, temp in enumerate(step):
        if ('*OUTPUT' in temp and 'HISTORY' in temp):
            possible_nodeset = step[j + 1].split(',')
            for item in possible_nodeset:
                if 'NSET' in item:
                    nodeset = item.split('=')[-1].strip()
                    key_para['bolt_node'] = nodeset
                    process_bar_read.add_record(['Node_Set', 'Succeed'])
        if ('CSTRESS' in temp and 'CDISP' in temp):
            key_para['relative_motion'] = 'YES'
            process_bar_read.add_record(['Relative_Motion', 'Found'])
    process_bar_read.set_status(19, 'Reading Bolt Node and Relative Motion Check')
    # 已经剔除掉了所有的注释语句,只剩下关键字和参数输入
    for i, step in enumerate(step_definition):
        if not key_para['bolt_force']:
            for j, temp in enumerate(step):
                if '*CLOAD' in temp:
                    key_para['bolt_force'] = step[j + 1].split(',')[-1].strip()
                    key_para['ini_assem'] = i + 1
                    process_bar_read.add_record(['Initial Assembly Bolt Force', 'Step_' + str(i + 1)])
                    break
        if not key_para['hot_assem']:
            for j, temp in enumerate(step):
                if '*TEMPERATURE' in temp:
                    key_para['hot_assem'] = i + 1
                    process_bar_read.add_record(['Hot Assembly', 'Step_' + str(i + 1)])
        if not key_para['p_dome']:
            pressure_name = []
            for j, temp in enumerate(step):
                if '*DSLOAD' in temp:
                    while '*' not in step[j + 1]:
                        pressure_name.append(step[j + 1].split(',')[-1].strip())
                        # process_bar_read.add_record(['Find DSLOAD', 'Step_' + str(i + 1)])
                        j = j + 1
                    break
    # 查找爆压数据
    if not key_para['bolt_force'].isdigit():
        temp = key_para['bolt_force'][1:-1]
        key_para['bolt_force'] = para_definition[temp]
        process_bar_read.add_record(['Find Bolt Force Value', key_para['bolt_force']])
    pressure_value = []
    for item in pressure_name:
        if not item.isdigit():
            item = item[1:-1]
            item = para_definition[item]
            if item.isdigit():
                pressure_value.append(float(item))
        else:
            pressure_value.append(float(item))
    key_para['p_dome'] = min(pressure_value)
    process_bar_read.add_record(['Find Peak Pressure', key_para['p_dome']])
    # 查找点火数据
    firing_step = []
    for i, step in enumerate(step_definition):
        ds_load = False
        firing = False
        for j, temp in enumerate(step):
            if '*DSLOAD' in temp:
                ds_load = True
            if temp.split(',')[-1].strip() in pressure_name:
                firing = True
        if ds_load and firing:
            firing_step.append(i)
    fixed_step = [firing_step[0]]
    cylinder_num = 0
    j = 1
    for i in range(len(firing_step) - 1):
        if (firing_step[i] + 1) != firing_step[i + 1]:
            fixed_step.append(firing_step[i + 1])
            if not cylinder_num:
                cylinder_num = firing_step[i] + 1 - firing_step[0]
            if cylinder_num != j:
                process_bar_read.add_record(['Firing Cylinder Number Not Equal', 'Step_' + str(i)])
            j = 1
        else:
            j += 1
    key_para['fixed_step'] = fixed_step
    key_para['cylinder_num'] = cylinder_num
    process_bar_read.add_record(['Find Fixed Steps', str(fixed_step)])
    process_bar_read.add_record(['Find Firing Cylinders', cylinder_num])
    process_bar_read.add_record(['**' + 'Read Main Input File' + '**', 'Finished'])
    return key_para


def read_dat_file(dat_file, key_para):
    start_read = False
    end_read = False
    process_bar_read.add_record(['**' + 'Read Dat File' + '**', 'Start'])
    with open(dat_file, 'rt', encoding='utf-8') as f:
        while True:
            line = f.readline().strip()
            if line:
                # 从这里才开始判断,估计能节约一些时间
                if 'P R O B L E M   S I Z E' in line:
                    start_read = True
                if start_read:
                    if 'NUMBER OF ELEMENTS IS' in line:
                        key_para['ELEM_NUM'] = line.split()[-1]
                    if 'NUMBER OF NODES IS' in line:
                        key_para['NODE_NUM'] = line.split()[-1]
                    if 'TOTAL NUMBER OF VARIABLES IN THE MODEL' in line:
                        key_para['TOTAL_VARIABLES'] = line.split()[-1]
                        end_read = True
                if end_read:
                    break
            else:
                break
    num_temp = 29
    text_temp = 'Searching model size'
    process_bar_read.set_status(num_temp, text_temp)
    process_bar_read.add_record(['**' + 'Read Dat File' + '**', 'Finished'])
    return key_para


def read_msg_file(msg_file, key_para):
    temp_list = []
    start_read = False
    num_temp = 30
    text_temp = 'Searching msg file'
    process_bar_read.set_status(num_temp, text_temp)
    process_bar_read.add_record(['**' + 'Read Msg File' + '**', 'Start'])
    with open(msg_file, 'rt', encoding='utf-8') as f:
        total_line = len(['' for line in f.readline()])
        f.seek(0, 0)
        for i, line in enumerate(f.readlines()):
            num_temp = 30 + int(i / total_line) * 15
            process_bar_read.set_status(num_temp, text_temp)
            if 'NUMBER OF FLOATING PT. OPERATIONS' in line:
                temp_list.append([])
                current_line = line.split('=')
                temp_list[-1].append(current_line[1].strip())
            if 'ELAPSED WALLCLOCK TIME' in line:
                current_line = line.split('=')
                temp_list[-1].append(current_line[1].strip())
            if 'TOTAL OF' in line:
                start_read = True
            if start_read:
                if 'ITERATIONS' in line:
                    key_para['TOTAL_INC'] = line.split()[0].strip()
                if 'WALLCLOCK' in line:
                    key_para['WALLCLOCK'] = line.split('=')[-1].strip()
    key_para['DETAILED_INC'] = temp_list
    process_bar_read.add_record(['**' + 'Read Msg File' + '**', 'Finished'])
    return key_para


def read_sta_file(sta_file, key_para):
    step_num = 1
    temp_list = []
    key_para['CAL_STATUS'] = 'FAILED'
    inc_list = key_para['DETAILED_INC']
    inc_num = 0
    process_bar_read.add_record(['**' + 'Read sta File' + '**', 'Start'])
    with open(sta_file, 'rt', encoding='utf-8') as f:
        for line in f.readlines():
            if 'DATE' in line:
                current_line = line.split('DATE')
                key_para['VERSION'] = current_line[0].strip()
                key_para['DATE'] = current_line[1].split('TIME')[0].strip()
            current_line = line.split()
            try:
                if current_line[0].isdigit():
                    if int(current_line[0]) == step_num:
                        temp_list.append(
                            [int(current_line[1]), int(current_line[5]), float(current_line[8])])
                        temp_inc_list = []
                        for i in range(int(current_line[5])):
                            temp_inc_list.append(inc_list[inc_num])
                            inc_num += 1
                        temp_list[-1].append(temp_inc_list)
                    else:
                        key_para['STEP_' + str(step_num)] = temp_list
                        temp_list = []
                        temp_list.append(
                            [int(current_line[1]), int(current_line[5]), float(current_line[8])])
                        temp_inc_list = []
                        for i in range(int(current_line[5])):
                            temp_inc_list.append(inc_list[inc_num])
                            inc_num += 1
                        temp_list[-1].append(temp_inc_list)
                        step_num += 1
            except Exception as e:
                print(e)
            if 'SUCCESSFULLY' in line:
                key_para['CAL_STATUS'] = 'SUCCESSFULLY'
            # 补充最后一个载荷步的结果
            key_para['STEP_' + str(step_num)] = temp_list
        num_temp = 45
        text_temp = 'Searching sta file'
        process_bar_read.set_status(num_temp, text_temp)
        process_bar_read.add_record(['**' + 'Read sta File' + '**', 'Finished'])
    del key_para['DETAILED_INC']
    return key_para


def read_gsk_file(gsk_file, main_input_file, gasket_input_file, store_folder):
    report_set = []
    gasket_behavior = {}
    gasket_section = {}
    behavior_field = {}
    gap_find = False
    process_bar_read.add_record(['**' + 'Read Gasket File' + '**', 'Start'])
    body_lds_max_row = int(local_settings['LDS_BODY_MAX_ROW'])
    current_line_num = 0
    with open(gsk_file, 'rt', encoding='utf-8') as f:
        num_temp = 45
        text_temp = 'Searching Gasket File'
        process_bar_read.set_status(num_temp, text_temp)
        while True:
            line = f.readline()
            if line:
                line = line.upper().strip()
                if not line.startswith('**'):
                    if line.startswith('*ELSET'):
                        set_name = line.split('=')[-1].strip()
                        report_set.append(set_name)
                        # process_bar_read.add_record(['Searching Gasket Set - ', set_name])
                    if line.startswith('*GASKET BEHAVIOR'):
                        behavior_name = line.split('=')[-1].strip()
                        gasket_behavior[behavior_name] = []
                        # process_bar_read.add_record(['Searching Gasket Behavior - ', behavior_name])
                    if line.startswith('*GASKET THICKNESS BEHAVIOR'):
                        if '*GASKET THICKNESS BEHAVIOR' in line:
                            line = f.readline()
                            while True:
                                if line.strip().startswith('**'):
                                    line = f.readline()
                                    continue
                                if line.strip().startswith('*'):
                                    if 'UNLOADING' in line:
                                        line = f.readline()
                                        gasket_behavior[behavior_name].append('**')
                                        continue
                                    gasket_behavior[behavior_name].append('**')
                                    break
                                gasket_behavior[behavior_name].append(line.strip())
                                behavior_field.setdefault(behavior_name, [])
                                if len(line.split(',')) == 4:
                                    field_num = line.split(',')[-1].strip()
                                    if field_num not in behavior_field[behavior_name]:
                                        behavior_field[behavior_name].append(field_num)
                                line = f.readline()
                    if '*GASKET SECTION' in line:
                        elset = line.split(',')
                        for item in elset:
                            if 'ELSET' in item:
                                elem_set_name = item.split('=')[-1].strip()
                            if 'BEHAVIOR' in item:
                                behavior_set_name = item.split('=')[-1].strip()
                        gap_value = 0
                        gap_find = True
                    if gap_find == True and '*' not in line:
                        gap_value = float(line.split(',')[1].strip())
                        gasket_section[elem_set_name] = [behavior_set_name, gap_value, 0]
                        # process_bar_read.add_record(['Searching Gasket Gap - ', str(gasket_section[elem_set_name])])
            else:
                break
    gasket_section, _ = connect_fatigue_database(gasket_section)
    num_temp = 90
    text_temp = 'Gasket Fatigue Data Read in Done'
    process_bar_read.set_status(num_temp, text_temp)
    delete_keys = []
    for keys in gasket_behavior:
        delete_check = True
        for item in gasket_section:
            if keys == gasket_section[item][0]:
                delete_check = False
                break
        if delete_check:
            delete_keys.append(keys)
    for keys in delete_keys:
        del gasket_behavior[keys]
    process_bar_read.add_record(['**' + 'Read Gasket File' + '**', 'Finished'])
    final_data = []

    for set_num, elem_set_name in enumerate(gasket_section):
        behavior_name = gasket_section[elem_set_name][0]
        gap_value = gasket_section[elem_set_name][1]
        field_num = behavior_field[behavior_name]
        gasket_lds = gasket_behavior[behavior_name]
        # 先得到loading
        # final_data[SET_NAME,[FIELD_NUM,[LOADING[[X],[Y]],LOADING2[[X],[Y]]...]..]
        if not field_num:
            field_num = [1]
        # 本身已经有一个场了,所以减一
        field_data = [[]]
        x = []
        y = []
        for i in range(len(field_num) - 1):
            field_data.append([])
        for item in gasket_lds:
            data = item.split(',')
            if item != '**':
                # 先判断field
                if len(data) > 3:
                    current_field = int(data[-1]) - 1
                else:
                    current_field = 0
                if float(data[0]) == 0:
                    if x:
                        field_data[current_field - 1].append([x, y])
                    x = [float(data[1]) + gap_value]
                    y = [float(data[0])]
                else:
                    x.append(float(data[1]) + gap_value)
                    y.append(float(data[0]))
        field_data[current_field].append([x, y])
        final_data.append([elem_set_name, field_data])
        # process_bar_read.add_record(['Set Gasket LDs + Gap - ', elem_set_name])

    fatigue_set = []
    for item in gasket_section:
        behavior_name = gasket_section[item][0]
        gasket_lds = gasket_behavior[behavior_name]
        field_num = behavior_field[behavior_name]
        if not field_num:
            field_num = [1]
        # BODY和STOPPER不要纳入疲劳集合,考虑一点安全系数,认为BODY的LD的数据为8行
        if len(gasket_lds) > body_lds_max_row * len(field_num):
            fatigue_set.append(item)
    process_bar_read.add_record(['Fatigue Element Set ', 'Done'])
    # 开始绘制LD曲线
    prop_cycle = plt.rcParams['axes.prop_cycle']
    color_list = prop_cycle.by_key()['color'] * 2

    fig, axs = plt.subplots()
    plot_line = []
    x_max = 0
    y_max = 0
    color_index = 0
    for item in final_data:
        elem_set_name = item[0]
        for j, current_field in enumerate(item[1]):
            color_index += 1
            for k, ld_data in enumerate(current_field):
                displacement = ld_data[0]
                force = ld_data[1]
                if x_max < displacement[-1]:
                    x_max = displacement[-1]
                if y_max < force[-1] and len(force) > 6:
                    y_max = force[-1]
                if k == 0:
                    if j == 0:
                        plot_line.append(axs.plot(displacement, force, color_list[color_index], label=elem_set_name))
                    else:
                        plot_line.append(
                            axs.plot(displacement, force, color_list[color_index],
                                     label=elem_set_name + '_' + str(j + 1)))
                else:
                    plot_line.append(axs.plot(displacement, force, color_list[color_index], dashes=[6, 2]))
    # X轴每隔0.2,0.4,0.6,0.8设置为一档
    # Y轴每隔1000,100,10,1设置为一档
    if x_max > 0.8:
        x_max = math.ceil(x_max / 0.8) * 0.8
    elif x_max > 0.6:
        x_max = math.ceil(x_max / 0.6) * 0.6
    elif x_max > 0.4:
        x_max = math.ceil(x_max / 0.4) * 0.4
    else:
        x_max = math.ceil(x_max / 0.2) * 0.2

    if y_max > 1000:
        y_max = math.ceil(y_max / 1000) * 1000
    elif y_max > 100:
        y_max = math.ceil(y_max / 100) * 100
    elif y_max > 10:
        y_max = math.ceil(y_max / 10) * 10
    else:
        y_max = math.ceil(y_max / 1) * 1

    axs.legend()
    axs.set_xlabel('Displacement (mm)')
    axs.set_ylabel('Line Load (N/mm)')
    axs.set_title('from ' + gasket_input_file, horizontalalignment='right', fontsize=8)
    axs.xaxis.set_major_locator(MultipleLocator(x_max / 5))
    axs.xaxis.set_minor_locator(MultipleLocator(x_max / 25))
    axs.yaxis.set_major_locator(MultipleLocator(y_max / 5))
    axs.yaxis.set_minor_locator(MultipleLocator(y_max / 25))
    axs.set_xlim(0, x_max)
    axs.set_ylim(0, y_max)
    plt.suptitle('LDs_' + main_input_file.split('.')[0].strip(), fontsize=14, fontweight='bold')
    plt.savefig(os.path.join(store_folder, main_input_file.split('.')[0].strip() + '_LDs.png'))
    num_temp = 93
    text_temp = 'Gasket LDs Generation Finished'
    process_bar_read.set_status(num_temp, text_temp)
    process_bar_read.add_record(['LDs Plot ', 'Done'])
    return report_set, fatigue_set, gasket_section
