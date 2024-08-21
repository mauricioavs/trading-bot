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

Install a python version:

pyenv install <version>
pyenv global <version>

test version:
python --version

## Send files

this is how files are sent via ssh:

Structure of following command:
scp -ri <key_path> <folder_to_send> ec2-user@<public_ip>:/home/ec2-user

command to send files and folders:
scp -ri keys/europe.pem production ec2-user@ec2-3-67-84-48.eu-central-1.compute.amazonaws.com:/home/ec2-user

## Run script
move to folder:
cd production

IMPORTANT: You may have to install big packages separately of requirements.txt like tensorflow due to size caching error of downloading multiple packages at once:
pip install --no-cache-dir tensorflow-cpu==2.15.0.post1

install the pip packages:
pip install --no-cache-dir -r requirements.txt

Note: Reboot instance if space is overloaded:
sudo reboot

also install:
sudo yum install tmux (asks confirmation)

run python script:
tmux new -s script
python run_bot.py

DONT FORGET TO ACTIVATE STATUSCAKE URL!!!

Now you can disconnect from server. When you want to check the results type:
tmux a -t script 





