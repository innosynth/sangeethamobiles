import datetime
import os
import sys
import shutil
from datetime import datetime
from backend.config import TenantSettings


settings = TenantSettings()

def file_storage(file_name,f_name):
    base_dir = settings.BASE_UPLOAD_FOLDER+"/upload_files"
    dt = str(int(datetime.utcnow().timestamp()))
    try:
        os.makedirs(base_dir, mode=0o777, exist_ok=True)
    except OSError as e:
        sys.exit("Can't create {dir}: {err}".format(
            dir=base_dir, err=e))

    output_dir = base_dir + "/"
    
    filename=file_name.filename
   
    txt = filename[::-1]
    splitted = txt.split(".",1)
    txt1 = splitted[0][::-1]
  
    files_name=f_name.split(".")
    

    save_full_path=f'{output_dir}{files_name[0]}{dt}.{txt1}'
   
    file_exe=f"{f_name}{dt}.{txt1}"
    with open(save_full_path, "wb") as buffer:
        shutil.copyfileobj(file_name.file, buffer)
        
    return save_full_path,file_exe