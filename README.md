installation:
install python 3.11.5
install dependencies
commands:
virtualenv env
env\scripts\activate (if u dont have access run this in powershell as admin: Set-ExecutionPolicy Unrestricted -Force)
pip install -r requirements.txt
python manage.py runserver

optional:
create a shortcut for the batch file and choose the icon from the static folder to run the server.

note:
change the gtk directory if it's needed inside accounts/views.py (os.add_dll_directory(r"C:\Program Files\GTK3-Runtime Win64\bin"))
