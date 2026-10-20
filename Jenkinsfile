
pipeline {
    agent any

    options {
        timestamps()
    }

    environment {
        DOCKERHUB_REPO = 'naitik7804/dynamic-load-balancer'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Python') {
            steps {
                sh '''
                    python3 --version
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/pip install -r requirements.txt
                    .venv/bin/pip install pytest
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '.venv/bin/python -m pytest tests/ -v'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build -t dynamic-load-balancer:${BUILD_NUMBER} .
                    docker tag dynamic-load-balancer:${BUILD_NUMBER} ${DOCKERHUB_REPO}:${BUILD_NUMBER}
                    docker tag dynamic-load-balancer:${BUILD_NUMBER} ${DOCKERHUB_REPO}:latest
                '''
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKERHUB_USER',
                    passwordVariable: 'DOCKERHUB_TOKEN'
                )]) {
                    sh '''
                        set +x
                        echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USER" --password-stdin
                        docker push ${DOCKERHUB_REPO}:${BUILD_NUMBER}
                        docker push ${DOCKERHUB_REPO}:latest
                        docker logout
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'CI/CD pipeline completed successfully, and the image was pushed to Docker Hub!'
        }
        failure {
            echo 'Pipeline failed. Check the stage logs.'
        }
    }
}
