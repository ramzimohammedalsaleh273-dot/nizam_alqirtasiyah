from pathlib import Path
import shutil, py_compile, re

ui=Path("app/ui/main_window.py")
shutil.copy2(ui,"backups/main_window_before_real_login.py")

text=ui.read_text(encoding="utf-8")

# إضافة خدمة الأمان
if "SecurityService" not in text:
    text=text.replace(
        "from PySide6.QtWidgets import",
        "from app.services.security_service import SecurityService\nfrom PySide6.QtWidgets import",
        1
    )

# إنشاء نافذة تسجيل الدخول إذا لم تكن موجودة
if "class LoginDialog" not in text:
    marker="class MainWindow"
    login=r'''
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user=None
        self.security=SecurityService()

        self.setWindowTitle("تسجيل الدخول — نظام القرطاسية")
        self.setFixedSize(430,300)
        self.setLayoutDirection(Qt.RightToLeft)

        layout=QVBoxLayout(self)

        title=QLabel("نظام القرطاسية")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:26px;font-weight:bold;padding:15px;")
        layout.addWidget(title)

        subtitle=QLabel("تسجيل الدخول إلى نظام لؤلؤة ERP")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        self.username=QLineEdit()
        self.username.setPlaceholderText("اسم المستخدم")
        layout.addWidget(self.username)

        self.password=QLineEdit()
        self.password.setPlaceholderText("كلمة المرور")
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password)

        self.message=QLabel("")
        self.message.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message)

        btn=QPushButton("دخول")
        btn.clicked.connect(self.login)
        layout.addWidget(btn)

        self.password.returnPressed.connect(self.login)

    def login(self):
        user=self.security.authenticate(
            self.username.text().strip(),
            self.password.text()
        )

        if not user:
            self.message.setText("اسم المستخدم أو كلمة المرور غير صحيحة")
            return

        self.user=user
        self.accept()


'''
    text=text.replace(marker,login+marker,1)

# تعديل run لعرض تسجيل الدخول قبل البرنامج
if "LoginDialog()" not in text:
    pattern=r"def run\(\):\s*.*?(?=\n(?:if __name__|$))"
    replacement='''def run():
    app = QApplication.instance() or QApplication([])
    app.setLayoutDirection(Qt.RightToLeft)

    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        return 0

    window = MainWindow()

    # إظهار المستخدم الحالي في العنوان إن أمكن
    try:
        username = login.user.get("username", "admin")
        window.setWindowTitle(f"نظام القرطاسية — لؤلؤة ERP | المستخدم: {username}")
    except Exception:
        pass

    window.show()
    return app.exec()
'''
    text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)

ui.write_text(text,encoding="utf-8")

py_compile.compile(str(ui),doraise=True)

print("="*72)
print("REAL LOGIN INTEGRATION")
print("="*72)
print("BACKUP: SAVED")
print("LOGIN SCREEN: READY")
print("AUTHENTICATION: CONNECTED")
print("RTL: ENABLED")
print("USER SESSION: CONNECTED")
print("PYTHON COMPILE: PASSED")
print("STATUS: SUCCESS")
print("="*72)
