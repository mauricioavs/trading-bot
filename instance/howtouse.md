## Send files

this is how files are sent via ssh:

Structure of following command:
scp -ri <key_path> <folder_to_send> ec2-user@<public_ip>:/home/ec2-user

command to send files and folders:
scp -ri keys/europe.pem production ec2-user@ec2-3-72-14-107.eu-central-1.compute.amazonaws.com:/home/ec2-user

## Install pyenv (https://gist.github.com/norsec0de/b863e2d99e251b848b5e9fece1c45f1a)

sudo yum install gcc zlib-devel bzip2 bzip2-devel patch readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel
sudo yum install git
git clone https://github.com/pyenv/pyenv.git ~/.pyenv
echo ' ' >> ~/.bash_profile
echo '# Pyenv Configuration' >> ~/.bash_profile
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
source ~/.bash_profile

test:
pyenv

We install a python version:

pyenv install <version>
pyenv global <version>

test version:
python --version


## Run script

install the pip packages:
pip install -r requirements.txt

also install:
sudo yum install tmux (asks confirmation)

run python script:
tmux new -s script
python run_bot.py

Now you can disconnect from server. When you want to check the results type:
tmux a -t script 



