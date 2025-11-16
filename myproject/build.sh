set -o errexit

pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py makemigrations myapp
python manage.py makemigrations room
python manage.py migrate 
