@NonCPS

def key_file = '/opt/password.txt'
def ec2_location = null

pipeline {
    agent { node { label 'master' } }
    environment {
        AWS_ACCESS_KEY_ID     = credentials('jenkins-aws-secret-key-id')
        AWS_SECRET_ACCESS_KEY = credentials('jenkins-aws-secret-access-key')
    }
    parameters {
        choice(name: 'REGION', choices: ['CN', 'FR', 'US'], description: 'where to deploy APP')
        string(name: 'CLIENT', defaultValue: 'learning-customer', description: 'what instance name of client APP')
    }
    stages{
        stage('GIT configuration Repo') {
            steps {
                dir('configuration') {
                    git credentialsId: 'slidemoon', branch: 'master', url: 'https://github.com/Learningtribes/configuration.git'
                    sh """
                    virtualenv /tmp/.venv2
                    . /tmp/.venv2/bin/activate
                    make requirements
                    """
                }
            }
        }
        stage('GIT inventory Repo') {
            steps {
                dir('inventory') {
                    git credentialsId: 'slidemoon', branch: 'master', url: 'https://github.com/Learningtribes/hawthorn_inventory.git'
                }
            }
        }
        stage('Setup region') {
            steps {
                script {
                    if (params.REGION == 'CN') {
                        ec2_location = 'ap-southeast-1'
                    } else if (params.REGION == 'FR') {
                        ec2_location = 'ap-southeast-1'
                    } else if (params.REGION == 'US') {
                        ec2_location = 'ap-southeast-1'
                    }
                }
            }
        }
        stage('Deploy certificate service') {
            steps {
                dir('configuration/playbooks') {
                    sh """
                    . /tmp/.venv2/bin/activate
                    ansible-playbook -i ../../inventory/hosts.ini -l "${params.CLIENT}_tenant" -u ubuntu --private-key /opt/instanceskey/"${ec2_location}"_platform_key.pem --vault-password-file "${key_file}" --skip-tags 'to-remove' lt_certs.yml
                    """
                }
            }
        }
    }
}