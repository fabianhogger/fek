import subprocess

def schedule_task(task_name, command, trigger="daily", start_time="16:00", days="MON,TUE,WED,THU,FRI,SAT,SUN"):
    try:
        subprocess.run(['schtasks', '/create', '/tn', task_name, '/tr', command, '/sc', trigger, '/st', start_time, '/d', days])
        print("Task created successfully!")
    except Exception as e:
        print(f"Failed to create task: {e}")

# Example usage:
schedule_task("MyTask", "python manage_tweets.py", trigger="daily", start_time="08:00")
