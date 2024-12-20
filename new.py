import streamlit as st
import boto3
import os
from io import BytesIO
from streamlit_option_menu import option_menu
import psycopg2
import datetime
s3=boto3.client('s3',aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))
BUCKET=os.getenv('BUCKET')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_PORT = os.getenv('DB_PORT')
conn=psycopg2.connect(host=DB_HOST,
                      database=DB_NAME,
                      user=DB_USER,
                      password=DB_PASS,
                      port=DB_PORT)
cur=conn.cursor()

if 'auth' not in st.session_state:
    st.session_state.auth = 0
with st.sidebar:
    if st.session_state.auth == 0:
        select=option_menu(menu_title=None,options=['Register','Login'],orientation="horizontal",)
        if select=="Register":
            username=st.text_input("enter your username")
            password=st.text_input("enter your password",type='password',help="should contain atleast 8 characters and atleast one number and special character")
            password1=st.text_input("re-enter your password",type='password',help="should contain atleast 8 characters and atleast one number and special character")
            dob=st.date_input("Enter your date of birth",min_value=datetime.date(1900, 1, 1))
            mail=st.text_input("enter your email address")
            mobile=st.text_input("enter your mobile number",max_chars=10)
            submit_button=st.button("submit")
            date=datetime.datetime.now()
            cur.execute(
                        """
                            CREATE TABLE IF NOT EXISTS storedata(USERNAME VARCHAR(50),PASSWORD VARCHAR(50),DATEOFBIRTH VARCHAR(50),MAIL VARCHAR(50),MOBILE VARCHAR(50),DATE VARCHAR(50))
                        """)
            cur.execute('select USERNAME,PASSWORD from storedata')
            rows = cur.fetchall()
            if submit_button:
                    if not username or not password:
                        st.warning("please enter the mandatory fields")
                        st.stop()
                    if password!=password1:
                        st.warning("Your password is not matching")
                        st.stop()
                    if len(password)<8 or sum(i.isnumeric() for i in password)<1 or sum(i.isupper() for i in password)<1 or sum(not(i.isalnum()) for i in password)<1:
                        st.warning("your password doesnt meet the critereia")
                        st.stop()
                    for row in rows:
                        if username == row[0]:
                            st.warning("user name already exists")
                            st.stop()
                    cur.execute(
                        """
                            CREATE TABLE IF NOT EXISTS storedata(USERNAME VARCHAR(50),PASSWORD VARCHAR(50),DATEOFBIRTH VARCHAR(50),MAIL VARCHAR(50),MOBILE VARCHAR(50),DATE VARCHAR(50))
                        """
                    )
                    cur.execute("INSERT INTO storedata(USERNAME, PASSWORD, DATEOFBIRTH, MAIL, MOBILE,DATE) VALUES (%s, %s, %s, %s, %s, %s)",(username,password,dob,mail,mobile,date))
                    conn.commit()
                    conn.close()
                    s3.put_object(Bucket=BUCKET,Key=f"{username}/",ACL="public-read")
                    st.success("You have been Registered successfully !!!")
                    
        if select=="Login":
            username=st.text_input("enter your registered username")
            password=st.text_input("enter your password",type="password")
            submit_button=st.button("submit")
            query=("SELECT * FROM storedata WHERE USERNAME = %s")
            value=(username,)
            cur.execute(query,value)
            rows=cur.fetchall()
            if submit_button:
                if not rows:
                    st.error("user is not registered")
                else:
                    if rows[0][1]==password:
                        st.session_state.auth = 1
                        st.session_state.user=username
                        st.success(f"Welcome to our website {username}")
                    else:
                        st.warning("you have entered wrong password plese check")
                
    #else:  # If authenticated
        #st.sidebar.success(f"Logged in as {username}")
    if st.button("Logout"):
        st.session_state.auth = 0  # Reset auth to 0 on logout
        st.session_state.user=""
        #st.experimental_rerun()

if st.session_state.auth == 1:

    if "upload_files" not in st.session_state:
        st.session_state.upload_files = []
    st.header(f"Welcome to your drive {st.session_state.user}")
    select=option_menu(menu_title=None,options=["upload/add",'view & download',"delete file"],orientation="horizontal")

    if select=="upload/add":
    # Upload multiple files
        files = st.file_uploader("You can upload any file", accept_multiple_files=True,)
        submit=st.button("upload")
        if submit and files:
            for file in files:
                file_data = BytesIO(file.read())
                s3.upload_fileobj(file_data, BUCKET, f"{st.session_state.user}/{file.name}",ExtraArgs={'ACL': 'public-read'})
                st.session_state.upload_files.extend(file)
            st.success("your files successfully upload to your drive")
        if submit and not files:
            st.warning("please enter atleast one file")

    # Check if files are uploaded
    if select=="view & download":
        col1,col2=st.columns(2)
        objects=s3.list_objects_v2(Bucket=BUCKET,Prefix=f"{st.session_state.user}/")
        if 'Contents' in objects:
            for obj in objects['Contents']:
                file_key=obj['Key']
                if file_key.endswith('/'):
                    continue
                file_obj=BytesIO()
                s3.download_fileobj(BUCKET,file_key,file_obj)
                file_obj.seek(0)
                col1.write(f"File Name: {(obj['Key']).split('/')[-1]}, Size: {obj['Size']} bytes")
                col2.download_button(
                    label=f"📩 {file_key.split('/')[-1]}",
                    data=file_obj,
                    file_name=file_key.split('/')[-1],
                    mime="application/octet-stream"
                )
        else:
            st.info("No files found in the bucket.")


    if select=="delete file":
        objects=s3.list_objects_v2(Bucket=BUCKET,Prefix=f"{st.session_state.user}/")
        if 'Contents' in objects:
            for obj in objects['Contents']:
                file_key = obj['Key']
                if file_key.endswith('/'):
                    continue
                
                file_name = file_key.split('/')[-1] 
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📄 {file_name}")
                with col2:
                    delete_button = st.button(f"Delete {file_name}", key=file_key)
                if delete_button:
                    s3.delete_object(Bucket=BUCKET, Key=file_key)
                    st.success(f"{file_name} has been deleted from the bucket.")
        else:
            st.write("No files found in the 'durgaprasad/' folder.")
