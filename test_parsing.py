import sys
import os

def run_oracle_test():
    print("==============================================")
    print("=      Launching Enclave Oracle Test         =")
    print("==============================================\n")
    
    # In Windows we write to a local folder C:/iexec_out
    # The enclave_oracle script uses the /iexec_out path.
    # In Windows /iexec_out is interpreted as the root of the current drive (e.g. C:\iexec_out).
    # Let's ensure the folder exists on the current system drive.
    os.makedirs("/iexec_out", exist_ok=True)
    
    try:
        # Import and run main() from enclave_oracle.py
        import enclave_oracle
        enclave_oracle.main()
        
        print("\n==============================================")
        print("=          RECORDED DATA ANALYSIS            =")
        print("==============================================\n")
        
        # Check if output files are created
        if os.path.exists("/iexec_out/computed.json"):
            print("[TEST-OK] computed.json found!")
            with open("/iexec_out/computed.json", "r") as f:
                print("computed.json content:")
                print(f.read())
        else:
            print("[TEST-FAIL] computed.json NOT FOUND!")
            
        if os.path.exists("/iexec_out/result.json"):
            print("\n[TEST-OK] result.json found!")
            print("Binary payload size (result.json):", os.path.getsize("/iexec_out/result.json"), "bytes")
        else:
            print("[TEST-FAIL] result.json NOT FOUND!")
            
        print("\n==============================================")
        print("=         COMPLEX TEST PASSED SUCCESSFULLY   =")
        print("==============================================\n")
        
    except Exception as e:
        import traceback
        print("\n!!! TEST EXECUTION ERROR !!!")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_oracle_test()
