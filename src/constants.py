import os

# 개발 환경에서는 현재 프로젝트 디렉토리 사용
if os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'src')):
    # 개발 환경
    rootdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
    datadir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    pkgdatadir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    localedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'po'))
else:
    # 설치된 환경
    rootdir = '/org/hamonikr/Chatbot'
    datadir = '/usr/share'
    pkgdatadir = '/usr/share/hamonikr-chatbot'
    localedir = '/usr/share/locale'

app_id           = 'org.hamonikr.Chatbot'
rel_ver          = '1.2.6'
version          = '1.2.6-dev'
build_type       = 'development'

project_url      = 'https://hamonikr.org'
bugtracker_url   = 'https://github.com/hamonikr/hamonikr-chatbot/issues'
help_url         = 'https://hamonikr.org'
translate_url    = 'https://github.com/hamonikr/hamonikr-chatbot'