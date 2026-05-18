import subprocess
import sys


def start_server(use_subprocess=False):
    """启动 Werkzeug 服务器
    
    Args:
        use_subprocess: 是否使用子进程启动，默认 False（阻塞模式）
    """
    cmd = [
        sys.executable, '-c',
        'from werkzeug.serving import make_server; import app; server = make_server("0.0.0.0", 5000, app.app, threaded=True); server.serve_forever()'
    ]
    
    if use_subprocess:
        subprocess.Popen(cmd, stdout=open('/dev/null', 'w'), stderr=open('/dev/null', 'w'))
        print('Server started on port 5000 (subprocess mode)')
    else:
        from werkzeug.serving import make_server
        import app
        server = make_server("0.0.0.0", 5000, app.app, threaded=True)
        print('Server started on port 5000 (blocking mode)')
        server.serve_forever()


if __name__ == '__main__':
    # 检查命令行参数
    use_subprocess = '--subprocess' in sys.argv
    start_server(use_subprocess=use_subprocess)