if __name__ == "__main__":
    try:
        from core.control import Controller
    except Exception as e:
        import traceback

        traceback.print_exc()
        input("导入错误，已阻塞")
        raise e
    else:
        Controller.run()
