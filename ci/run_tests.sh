#!/bin/bash -x
. /edx/app/edxapp/edxapp_env

. /edx/app/edxapp/nodeenvs/edxapp/bin/activate
. /edx/app/edxapp/venvs/edxapp/bin/activate

cd /edx/app/edxapp/edx-platform

paver test_system -C -c "--cov-append" --fasttest
paver test_lib -C -c "--cov-append"
paver coverage

