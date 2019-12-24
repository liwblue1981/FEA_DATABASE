from django.shortcuts import render, HttpResponse, redirect
from django.http import JsonResponse
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
# 导入message库
from django.contrib import messages
# 这句话用来得到UserModel对象,
from user.models import UserModel
from common.local_settings import local_settings
from lib import local_function
import paramiko
import json
import os
import time


# Create your views here.
class LoginView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'login.html')

    def post(self, request, *args, **kwargs):
        name = request.POST.get('username')
        password = request.POST.get('password')
        # user虽然打印出来是Wei.Li,那是因为我采用了__str__方法定义,但它本身还是UserModel对象
        user = authenticate(username=name, password=password)  # type: UserModel
        if user:
            login(request, user)
            request.session['login'] = name
            # request.session['username'] = UserModel.objects.filter(username=name).first()
            request.session['username'] = user.first_name + '.' + user.last_name
            return redirect('/home/')
        return render(request, 'login.html')


class HomeView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        MAX_FIRING_CYCLE = local_settings['MAX_FIRING_CYCLE']
        MAX_FATIGUE_NUM = local_settings['MAX_FATIGUE_NUM']
        return render(request, 'home.html', context=locals())


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('/login/')


class SetFatigue(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('OK')

    def post(self, request, *args, **kwargs):
        # 得到前端传入的数据
        res = json.loads(request.body.decode('utf-8'))
        main_input_file = res.get('main_input_file')
        file_name = main_input_file.split('/')[-1].split('.')[0]
        store_folder = os.path.join(local_settings['SERVER_LOCATION'], file_name, file_name + '_backup.json')
        with open(store_folder, 'rt', encoding='utf-8') as f:
            res = json.load(f)
        return JsonResponse(res)


class ReadMain(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('OK')

    def post(self, request, *args, **kwargs):
        # 设置全局变量用于连接服务器,认为对于一个项目,只有一个服务器需要连接
        # 1. 得到前端传入的数据
        res = json.loads(request.body.decode('utf-8'))
        hostname = res.get('server_name').lower()
        server_location = res.get('server_location')
        main_input_file = res.get('main_input_file')
        gasket_input_file = res.get('gasket_input_file')
        if not server_location.endswith('/'):
            server_location += '/'
        if not main_input_file.endswith('.inp'):
            main_input_file += '.inp'
        if not gasket_input_file.endswith('.inp'):
            gasket_input_file += '.inp'
        # # 建立SFTP链接,读取主文件,垫片文件等
        # ssh = paramiko.SSHClient()
        # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # 获取文件路径,文件名称,主机名称
        # local_location暂时没有用,我还是无法操作每个人自己的电脑,因为没有访问权限
        local_location = res.get('local_location')
        if not local_location.endswith('/'):
            local_location += '/'
        # 2. 指定需要下载的文件
        download_list = [main_input_file.rsplit('.', 1)[0] + extension for extension in
                         ['.inp', '.dat', '.msg', '.sta']]
        download_list.append(gasket_input_file)
        # 3. 建立下载路径,因为是在本机上操作,所以不存在不能建立文件夹的情况,所以就不try了
        file_name = main_input_file.split('/')[-1].split('.')[0]
        store_folder = os.path.join(local_settings['SERVER_LOCATION'], file_name)
        if not os.path.exists(store_folder):
            os.makedirs(store_folder)
            time.sleep(2)
        local_function.process_bar_read.set_archive_path(os.path.join(store_folder, file_name + '_readprocess.log'))
        local_function.process_bar_read.add_record(['Create Backup Path', 'Successfully'])
        num_progress = 5
        text_progress = 'Create Backup Path Successfully'
        local_function.process_bar_read.set_status(num_progress, text_progress)
        # 通过ajax可以把前台的数据传过来,可以获得hostname, server_location, local_location
        # 因为自己装的服务器不在公司的域里面,所以没有办法通过sftp进行访问,正式上线,需要更改开关
        if local_settings['CONNECT_LOCAL']:
            server_location = '/usr/local/fea_database/fea_library/test_readin/'
            main_input_file = 'FEA19-0840.inp'
            gasket_input_file = 'gasket-FEA19-0840-test.inp'
        else:
            # 4. 尝试建立链接
            # 5. 尝试下载文件
            text_value = 'Connect to Server ' + hostname
            res = local_function.connect_to_server(hostname, local_function.process_bar_read, 10, text_value,
                                                   download_list, server_location, store_folder)
            if not res:
                return HttpResponse('Failed')

        # 6. 读取主文件
        try:
            key_para = local_function.read_main_file(os.path.join(store_folder, download_list[0]))
            num_progress = 28
            text_progress = 'Finished Reading input File'
            local_function.process_bar_read.set_status(num_progress, text_progress)
        except Exception as e:
            local_function.process_bar_read.add_record(['Input File Read', 'Failed'])
            local_function.process_bar_read.add_record(['*' * 10 + 'Error', str(e)])
        # 7. 读取主文件.dat
        try:
            key_para = local_function.read_dat_file(os.path.join(store_folder, download_list[1]), key_para)
            num_progress = 30
            text_progress = 'Finished Reading dat File'
            local_function.process_bar_read.set_status(num_progress, text_progress)
        except Exception as e:
            local_function.process_bar_read.add_record(['Dat File Read', 'Failed'])
            local_function.process_bar_read.add_record(['*' * 10 + 'Error', str(e)])
        # 8. 读取主文件.msg
        try:
            key_para = local_function.read_msg_file(os.path.join(store_folder, download_list[2]), key_para)
            num_progress = 45
            text_progress = 'Finished Reading message File'
            local_function.process_bar_read.set_status(num_progress, text_progress)
        except Exception as e:
            local_function.process_bar_read.add_record(['Msg File Read', 'Failed'])
            local_function.process_bar_read.add_record(['*' * 10 + 'Error', str(e)])
        # 9. 读取主文件.sta
        try:
            key_para = local_function.read_sta_file(os.path.join(store_folder, download_list[3]), key_para)
            num_progress = 45
            text_progress = 'Finished Reading sta File'
            local_function.process_bar_read.set_status(num_progress, text_progress)
        except Exception as e:
            local_function.process_bar_read.add_record(['Sta File Read', 'Failed'])
            local_function.process_bar_read.add_record(['*' * 10 + 'Error', str(e)])

        # 读入request里面的数据
        res = local_function.connect_request_database(file_name)
        for keys in res:
            key_para[keys] = res[keys]
        try:
            # 读取gasket数据
            report_set, fatigue_set, gasket_section = local_function.read_gsk_file(
                os.path.join(store_folder, download_list[4]), main_input_file, gasket_input_file, store_folder)
        except Exception as e:
            local_function.process_bar_read.add_record(['Gasket File Read', 'Failed'])
            local_function.process_bar_read.add_record(['*' * 10 + 'Error', str(e)])

        key_para['fatigue_set'] = fatigue_set
        key_para['report_set'] = report_set + fatigue_set
        key_para['gasket_section'] = gasket_section
        key_para['lds_title'] = file_name + '_LDs.png'
        # LD的存储地址和显示地址是不一样的,显示的时候,直接显示static就好,因为路由就只配置了这个路径
        key_para['lds_saved'] = '/static/' + file_name + '/' + file_name + '_LDs.png'
        log_file = os.path.join(local_settings['SERVER_LOCATION'], file_name, file_name + '_postprocess.dat')
        with open(log_file, 'w', encoding='utf-8') as f:
            for keys in key_para:
                if 'STEP' not in keys:
                    f.write(keys.ljust(20) + str(key_para[keys]).ljust(100) + '\n')
        with open(log_file, 'a', encoding='utf-8') as f:
            for keys in key_para:
                if 'STEP' in keys:
                    f.write('**' + '=' * 30 + '**')
                    f.write(keys.ljust(20) + '\n')
                    f.write('INC'.ljust(20) + 'TOTAL ITERS'.ljust(20) + 'INC TIME'.ljust(20) + 'ITERS NO.'.ljust(
                        20) + 'FLOATING NUM'.ljust(20) + 'WALLCLOCK'.ljust(20) + '\n')
                    detailed_step = key_para[keys]
                    for cur_inc in range(len(detailed_step)):
                        cur_string = detailed_step[cur_inc]
                        first_inc = cur_string[3][0]
                        temp_string = str(cur_string[0]).ljust(20) + str(cur_string[1]).ljust(20) + str(
                            cur_string[2]).ljust(20) + '1'.ljust(20) + first_inc[0].ljust(20) + first_inc[1].ljust(
                            20) + '\n'
                        f.write(temp_string)
                        for detail_inc in range(len(cur_string[3]) - 1):
                            temp_string = ' ' * 60 + str(detail_inc + 1).ljust(20) + cur_string[3][detail_inc + 1][
                                0].ljust(20) + cur_string[3][detail_inc + 1][1].ljust(20) + '\n'
                            f.write(temp_string)
        local_function.process_bar_read.add_record(['Write to Dat File', 'Finished'])
        json_file = os.path.join(local_settings['SERVER_LOCATION'], file_name, file_name + '_backup.json')
        key_para['hostname'] = hostname
        key_para['server_path'] = server_location
        key_para['main_input_file'] = main_input_file
        key_para['gasket_input_file'] = gasket_input_file
        key_para['local_location'] = local_location
        local_function.process_bar_read.add_record(['Write to Json File', 'Finished'])
        key_para['process_log'] = local_function.process_bar_read.record
        with open(json_file, 'wt', encoding='utf-8') as f:
            json.dump(key_para, f)
            num_progress = 95
            text_progress = 'Finished Dumping Results'
            local_function.process_bar_read.set_status(num_progress, text_progress)
        # 所有的信息都读入以后,把生成的文件上传到服务器的路径中
        upload_files = ['_readprocess.log', '_backup.json', '_postprocess.dat', '_LDs.png', '_recordprocess.log']
        upload_files = [file_name + files for files in upload_files]
        local_function.process_bar_process.set_archive_path(
            os.path.join(store_folder, file_name + '_recordprocess.log'))
        local_function.process_bar_process.set_status(15, 'Start Upload Files')
        # 1. 链接数据库
        # 2. 尝试上传文件
        text_value = 'Connect to Server ' + hostname
        res = local_function.connect_to_server(hostname, local_function.process_bar_process, 10, text_value,
                                               upload_files, server_location, store_folder, down_up='Upload')
        if not res:
            return HttpResponse('Failed')
        return JsonResponse(key_para)


class GenerateInput(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('OK')

    def post(self, request, *args, **kwargs):
        # 需要的数据共分为两部分,一部分是属于在read_main的时候读入的数据,这部分数据不可更改,另一部分是在前端用户自己输入的数据
        # 得到前端传入的数据
        res_web = json.loads(request.body.decode('utf-8'))
        main_input_file = res_web.get('main_input_file')
        file_name = main_input_file.split('/')[-1].split('.')[0]
        read_path = os.path.join(local_settings['SERVER_LOCATION'], file_name)
        with open(os.path.join(read_path, file_name + '_backup.json'), 'rt', encoding='utf-8') as f:
            res_server = json.load(f)
        write_path1 = os.path.join(read_path, file_name + '_chg_postprocess_header.py')
        space_num = 30
        level_f_space = 100
        level_s_space = 50
        comment_set = '#' * 10
        with open(write_path1, 'wt', encoding='utf-8') as f:
            f.write(comment_set + 'INPUT PARAMETERS FROM WEB'.center(level_f_space) + comment_set + '\n')
            f.write('#cal_in_server = '.ljust(space_num) + res_server['hostname'] + '\n')
            f.write('#main_file = '.ljust(space_num) + res_server['main_input_file'] + '\n')
            f.write('#gasket_file = '.ljust(space_num) + res_server['gasket_input_file'] + '\n')
            f.write('#local_location = '.ljust(space_num) + res_server['local_location'] + '\n')
            f.write('#fea_number = '.ljust(space_num) + res_server['request_number'] + '\n')
            f.write('#requestor = '.ljust(space_num) + res_server['submit_name'] + '\n')
            f.write('#analyst = '.ljust(space_num) + res_server['analyst_name'] + '\n')
            f.write('#customer = '.ljust(space_num) + res_server['customer'] + '\n')
            f.write('#project_name = '.ljust(space_num) + res_server['project_name'] + '\n')
            f.write('#request_title = '.ljust(space_num) + res_server['title'] + '\n')
            f.write('#bolt_node_set = '.ljust(space_num) + res_server['bolt_node'] + '\n')
            f.write('#bolt_force = '.ljust(space_num) + res_server['bolt_force'] + '\n')

            f.write(comment_set + 'GLOBAL SETTINGS'.center(level_s_space) + comment_set + '\n')
            f.write('saved_path = ' + res_server['server_path'] + '\n')
            f.write('main_file_name = ' + res_server['main_input_file'].rsplit('.', 1)[0] + '\n')
            f.write('total_cylinder_num = ' + str(res_web['total_cylinder_num'].split()[0]) + '\n')
            f.write('firing_pressure = ' + str(res_server['p_dome']) + '\n')
            # "FB, HB1, HB2,..."
            temp_set = res_web['report_set'].split(',')
            f.write('report_set =' + str(temp_set) + '\n')
            temp_set = res_web['excel_set'].split(',')
            f.write('excel_set = ' + str(temp_set) + '\n')
            # ["aa", "bb"]
            temp_set = res_web['add_elem_set_name']
            f.write('add_elem_set = ' + str(temp_set) + '\n')
            # ["1,2,3", "4,5,6"]
            f.write('add_elem_list = ' + str(res_web['add_elem_set_list']) + '\n')

            f.write(comment_set + 'BORE DISTORTION SETTING'.center(level_s_space) + comment_set + '\n')
            f.write('bore_distortion_step = ' + str(res_web['bore_distortion_step']) + '\n')
            f.write('bore_distortion_order = ' + str(res_web['bore_distortion_order']) + '\n')
            f.write('bore_distortion_radius = ' + str(res_web['bore_distortion_radius']) + '\n')
            if 'boredistortion_manually' in res_web:
                f.write('boredistortion_manually = True\n')
            else:
                f.write('boredistortion_manually = False\n')
            bore_node_set = res_web['boredistortion_manually_nodeset'].strip()
            if not bore_node_set:
                bore_node_set = 'False'
            f.write('boredistortion_manually_nodeset = ' + bore_node_set + '\n')
            f.write('boredistortion_auto_points = ' + str(res_web['boredistortion_auto_points']) + '\n')
            f.write('boredistortion_auto_layers = ' + str(res_web['boredistortion_auto_layers']) + '\n')
            f.write('boredistortion_auto_linername = ' + str(res_web['boredistortion_auto_linername']) + '\n')
            f.write('boredistortion_auto_starts = ' + str(res_web['boredistortion_auto_starts']) + '\n')
            f.write('boredistortion_auto_ends = ' + str(res_web['boredistortion_auto_ends']) + '\n')

            f.write(comment_set + 'CAM JOURNAL DISTORTION SETTING'.center(level_s_space) + comment_set + '\n')
            f.write('cam_distortion_step = ' + str(res_web['cam_distortion_step']) + '\n')
            f.write('add_cam_node_list = ' + str(res_web['add_cam_node_list']) + '\n')

            f.write(comment_set + 'BORE DISTANCE SETTING'.center(level_s_space) + comment_set + '\n')
            f.write('distance_between_bores = ' + str(res_web['distance_between_bores']) + '\n')
            f.write('bore_center_y = ' + str(res_web['bore_center_y']) + '\n')
            f.write('firing_cylinder_name = ' + str(res_web['firing_cylinder_name']) + '\n')
            f.write('firing_cylinder_x_center = ' + str(res_web['firing_cylinder_x_center']) + '\n')
            f.write('firing_cylinder_x_min = ' + str(res_web['firing_cylinder_x_min']) + '\n')
            f.write('firing_cylinder_x_max = ' + str(res_web['firing_cylinder_x_max']) + '\n')
            f.write('firing_name_list = ' + str(res_web['firing_name_list']) + '\n')

            f.write(comment_set + 'STEP SETTING'.center(level_s_space) + comment_set + '\n')
            f.write('firing_cylinder_num = ' + str(res_server['cylinder_num']) + '\n')
            f.write('relative_motion = ' + res_server['relative_motion'] + '\n')
            f.write('ini_assem = ' + str(res_server['ini_assem']) + '\n')
            f.write('hot_assem = ' + str(res_server['hot_assem']) + '\n')
            f.write('fixed_step = ' + str(res_server['fixed_step']) + '\n')

            f.write(comment_set + 'FATIGUE SETTING'.center(level_s_space) + comment_set + '\n')

            temp_set = res_web['fatigue_set'].split(',')
            fatigue_num = len(temp_set)
            f.write('fatigue_set = ' + str(temp_set) + '\n')
            fatigue_id = res_web['fatigue_id']
            f.write('fatigue_id = ' + str(fatigue_id) + '\n')
            gasket_section = res_server['gasket_section']
            fatigue_info = {}
            for i in range(fatigue_num):
                current_id = int(fatigue_id[i])
                if current_id:
                    for keys in gasket_section:
                        if gasket_section[keys][2] == current_id:
                            try:
                                fatigue_info[str(current_id)] = gasket_section[keys][3]
                            except Exception as e:
                                fatigue_info[str(current_id)] = [['PRELOAD_VALUE'], ['LOAD_VALUE'],
                                                                 ['FATIGUE_LIMIT_LOAD_ARRAY']]

            data_example = '''
            {
                ID: [
                        [PRELOAD_VALUE],
                        [LOAD_VALUE],
                        [[FATIGUE_LIMIT_LOAD1], [FATIGUE_LIMIT_LOAD2], ...],
                    ]
            }
            '''
            f.write(comment_set + 'FATIGUE DATA FORMAT EXAMPLE'.center(level_s_space) + comment_set + '\n')
            f.write('\'\'\'' + '\n')
            f.write(data_example + '\n')
            f.write('\'\'\'' + '\n')
            f.write('fatigue_limit = { \n')
            for k, v in fatigue_info.items():
                f.write(str(k) + ': [ \n')
                f.write(str(v[0]) + ',\n')
                f.write(str(v[1]) + ',\n')
                f.write(str(v[2]) + ',\n')
                f.write('], \n')
            f.write('} \n')

            f.write(comment_set + 'FINISHED INPUT READING'.center(level_f_space) + comment_set + '\n')
        return JsonResponse({'file_name': file_name + '_chg_postprocess_header.py', })


class ShowLog(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('OK')

    def post(self, request, *args, **kwargs):
        # 得到前端传入的数据
        res = json.loads(request.body.decode('utf-8'))
        main_input_file = res.get('main_input_file')
        file_name = main_input_file.split('/')[-1].split('.')[0]
        store_folder = os.path.join(local_settings['SERVER_LOCATION'], file_name, file_name + '_backup.json')
        with open(store_folder, 'rt', encoding='utf-8') as f:
            res = json.load(f)
        return JsonResponse(res)


class ShowProgressReading(View):
    def get(self, request, *args, **kwargs):
        temp = local_function.process_bar_read.get_status()
        return JsonResponse(temp)


class ShowProgressProcessing(View):
    # 2. Process过程会持续调用该函数
    def get(self, request, *args, **kwargs):
        # 需要从服务器中读取,位于set_archive_path, 用get方法来拿前台的GET请求值,get方法的好处是,如果没有该值,返回None
        hostname = request.GET.get('hostname')
        temp = {'HostName': 'False'}
        if hostname:
            temp = local_function.read_log_from_server(hostname)
        return JsonResponse(temp)


class StartProcess(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('OK')

    def post(self, request, *args, **kwargs):
        # 得到前端传入的数据
        res = json.loads(request.body.decode('utf-8'))
        hostname = res.get('server_name').lower()
        server_location = res.get('server_location')
        main_input_file = res.get('main_input_file')
        file_name = main_input_file.split('/')[-1].split('.')[0]
        store_folder = os.path.join(local_settings['SERVER_LOCATION'], file_name)
        # 1. Process按钮点击执行到这里

        # 可以开始准备执行一个脚本了,周一先测试该脚本独立在服务器上运行,不需要考虑前后端交互,任务是顺利执行所有ABAQUS的后处理程序.


        return HttpResponse('OK')
