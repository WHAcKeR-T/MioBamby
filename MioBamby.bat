@echo off
echo Activating virtual environment...
call env\scripts\activate
echo Virtual environment activated.
echo Starting Django development server...
python manage.py runserver
pause