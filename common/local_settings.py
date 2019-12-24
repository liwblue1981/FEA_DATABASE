from fea_library import settings
import os

local_settings = {
    'MAX_FIRING_CYCLE': 50,
    'MAX_FATIGUE_NUM': 20,
    'LDS_BODY_MAX_ROW': 8,
    # 这里的开关用于测试,只是访问本机的文件,而非直接连接服务器35, 36.
    'CONNECT_LOCAL': False,
    'USER_NAME': 'liw00073',
    'PASSWORD': 'python111',
    # 服务器存储过程文件路径
    'SERVER_LOCATION': os.path.join(settings.BASE_DIR, 'CHG_FILE_BACKUP'),
    # 服务器名称对应的IP地址
    'shnhcnlx031': '10.216.161.67',
    'shnhcnlx032': '10.216.161.69',
    'shnhcnlx033': '10.216.161.81',
    'shnhcnlx035': '10.216.161.83',
    'shnhcnlx036': '10.218.32.245',
    'request_server': {
        'host': '10.131.12.156',
        'user': 'liw00073',
        'password': 'liw00073',
        'database': 'fm_projects',
        'request_table': 'rq_requests',
        'project_table': 'rq_projects',
        'user_table': 'users',
    },
    'fatigue_server': {
        'host': '10.131.12.156',
        'user': 'liw00073',
        'password': 'liw00073',
        'database': 'FEADataBase',
        'fatigue_table': 'tfatigue',
    },
}
