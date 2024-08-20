from login import login
from mapmaker import *

if __name__ == "__main__":
    try :
        client = login()
    except Exception as e:
        print("Error: {0}".format(e))
        exit(1)

    generate_maps(client, True)

    
