import os
import sys
from django.core.management import call_command

if __name__ == '__main__':
    app_name = sys.argv[1]
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app_template')
    call_command('startapp', app_name, template=template_path)
    # سپس منتقل به apps/
    os.rename(app_name, f'apps/{app_name}')