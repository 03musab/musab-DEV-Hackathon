from agent_core import run_agent
from dashboard import launch_dashboard
from integrations import setup_integrations

def main():
    print("Starting General AI Agent...")
    setup_integrations()
    run_agent()
    launch_dashboard()

if __name__ == "__main__":
    main()