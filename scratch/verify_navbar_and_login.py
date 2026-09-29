import os
import sys
import django

sys.path.insert(0, r'd:\Intership project\django-bookmyshow-clone')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from django.test import Client

c = Client()

# 1. Anonymous test
r_anon = c.get('/')
assert 'Admin Dashboard' not in r_anon.content.decode('utf-8'), 'Anon should not see Admin Dashboard'
print('[PASS] Anonymous user does not see Admin Dashboard')

# 2. Check login page
r_login = c.get('/login/')
login_html = r_login.content.decode('utf-8')
assert 'data-user="testuser"' in login_html, 'testuser demo button should exist'
assert 'data-user="admin"' in login_html, 'admin demo button should exist'
assert 'data-user="dheekshith"' not in login_html, 'dheekshith demo button should NOT exist'
print('[PASS] Login page has testuser and admin quick login, but NOT dheekshith')

# 3. testuser test
c_test = Client()
login_res = c_test.post('/login/', {'username': 'testuser', 'password': 'testpass123'})
r_home_test = c_test.get('/')
test_html = r_home_test.content.decode('utf-8')
assert 'Admin Dashboard' not in test_html, 'testuser must NOT see Admin Dashboard!'
dash_test = c_test.get('/dashboard/', follow=False)
assert dash_test.status_code == 302, f'testuser must be blocked from /dashboard/, got {dash_test.status_code}'
print('[PASS] testuser DOES NOT see Admin Dashboard in navbar and is BLOCKED from /dashboard/')

# 4. admin test
c_admin = Client()
c_admin.post('/login/', {'username': 'admin', 'password': 'admin123'})
r_home_admin = c_admin.get('/')
admin_html = r_home_admin.content.decode('utf-8')
assert 'Admin Dashboard' in admin_html, 'admin MUST see Admin Dashboard in navbar'
dash_admin = c_admin.get('/dashboard/', follow=False)
assert dash_admin.status_code == 200, f'admin MUST access /dashboard/, got {dash_admin.status_code}'
print('[PASS] admin SEES Admin Dashboard in navbar and CAN access /dashboard/')

print('\nALL USER REQUIREMENTS VERIFIED SUCCESSFULLY!')
