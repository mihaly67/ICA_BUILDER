import os
import sys
import subprocess

VPS_HOST = os.environ.get("VPS_HOST", "5.189.163.88")
VPS_PWD = os.environ.get("VPS_PWD")
VPS_USER = os.environ.get("VPS_USER", "misi")

def run_on_vps(cmd):
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{VPS_USER}@{VPS_HOST}", cmd]
    env = os.environ.copy()
    if VPS_PWD:
        ssh_cmd = ["sshpass", "-e"] + ssh_cmd
        env["SSHPASS"] = VPS_PWD

    try:
        result = subprocess.run(ssh_cmd, check=True, capture_output=True, text=True, env=env)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def upload_to_vps(local_file, remote_target):
    scp_cmd = ["scp", "-o", "StrictHostKeyChecking=no", local_file, f"{VPS_USER}@{VPS_HOST}:{remote_target}"]
    env = os.environ.copy()
    if VPS_PWD:
        scp_cmd = ["sshpass", "-e"] + scp_cmd
        env["SSHPASS"] = VPS_PWD

    try:
        subprocess.run(scp_cmd, check=True, capture_output=True, text=True, env=env)
        return True, "Feltöltés sikeres."
    except subprocess.CalledProcessError as e:
        return False, e.stderr

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Használat:")
        print("  python3 vps_bridge.py 'parancs a vps-en'")
        print("  python3 vps_bridge.py --upload <local_file> <remote_target>")
        sys.exit(1)

    if sys.argv[1] == '--upload' and len(sys.argv) == 4:
        success, msg = upload_to_vps(sys.argv[2], sys.argv[3])
        if success:
            print(msg)
        else:
            print(f"Hiba a feltöltés során: {msg}", file=sys.stderr)
            sys.exit(1)
    else:
        cmd_to_run = " ".join(sys.argv[1:])
        success, msg = run_on_vps(cmd_to_run)
        print(msg)
        if not success:
            print(f"Hiba a parancs futtatásakor: {msg}", file=sys.stderr)
            sys.exit(1)
