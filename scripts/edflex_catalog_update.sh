sudo -H -u edxapp bash << EOF
source /edx/app/edxapp/edxapp_env
cd /edx/app/edxapp/edx-platform
python manage.py lms get_external_catalog_resources --settings=aws
EOF
