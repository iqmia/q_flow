from q_flow import create_app
from q_flow.config import LocalConfig

app = create_app(LocalConfig)

if __name__ == '__main__':
    app.run("0.0.0.0", 5002)