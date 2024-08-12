
from app import app, socketio

if __name__ == "__main__":
    import eventlet
    import eventlet.wsgi

    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
