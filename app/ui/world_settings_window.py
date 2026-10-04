from __future__ import annotations
from PySide6.QtCore import QLocale
from PySide6.QtPrintSupport import QPrinterInfo
from PySide6.QtWidgets import QVBoxLayout,QLabel,QLineEdit,QPushButton,QHBoxLayout,QFileDialog
from app.ui.modern_ui import SettingsWindow as _BaseSettingsWindow, SearchableCombo


def world_currencies():
    found={}
    try:
        iso=getattr(QLocale,'CurrencyIsoCode',None)
        if iso is None:
            iso=getattr(getattr(QLocale,'CurrencySymbolFormat',object),'CurrencyIsoCode',None)
        for loc in QLocale.matchingLocales(QLocale.AnyLanguage,QLocale.AnyScript,QLocale.AnyCountry):
            try:
                code=str(loc.currencySymbol(iso)) if iso is not None else ''
                if not code or len(code)!=3:continue
                text_value=f'{code} — {loc.name()}'
                found[code]=text_value
            except Exception:continue
    except Exception:pass
    common={'SAR':'SAR — الريال السعودي — السعودية','YER':'YER — الريال اليمني — اليمن','USD':'USD — الدولار الأمريكي — الولايات المتحدة','EUR':'EUR — اليورو — منطقة اليورو','GBP':'GBP — الجنيه الإسترليني — المملكة المتحدة'}
    found.update(common)
    return sorted([(v,k) for k,v in found.items()],key=lambda x:x[0].lower())


class WorldSettingsWindow(_BaseSettingsWindow):
    def _build_pages(self):
        p,l=self.page('بيانات المنشأة');self.company=QLineEdit(self._setting_get('company_name','قرطاسية لؤلؤة الأربعين النموذجية'));self.address=QLineEdit(self._setting_get('company_address',''));self._add_save(l,[('اسم المنشأة',self.company,'company_name'),('العنوان',self.address,'company_address')]);self.stack.addWidget(p)
        p,l=self.page('اللغة والاتجاه');lang=SearchableCombo([(x,x) for x in getattr(__import__('app.ui.modern_ui',fromlist=['LANGUAGES']),'LANGUAGES',[]) ]);lang.setCurrentText(self._setting_get('language','العربية'));direction=SearchableCombo([('يمين إلى يسار — RTL','rtl'),('يسار إلى يمين — LTR','ltr'),('تلقائي حسب اللغة','auto')]);direction.setCurrentData(self._setting_get('ui_direction','rtl'));self._add_save(l,[('اللغة — ابحث باسم اللغة',lang,'language'),('اتجاه الواجهة — معالج بحث',direction,'ui_direction')]);self.stack.addWidget(p)
        p,l=self.page('العملة — بحث عالمي');cur=SearchableCombo(world_currencies());cur.setCurrentData(self._setting_get('currency_code','SAR'));self._add_save(l,[('العملة — الاختصار أو الاسم أو الدولة/المنطقة',cur,'currency_code')]);self.stack.addWidget(p)
        p,l=self.page('التاريخ والوقت');date=SearchableCombo([(x,x) for x in ['dd/MM/yyyy','MM/dd/yyyy','yyyy/MM/dd','yyyy-MM-dd','dd-MM-yyyy','dd.MM.yyyy','dddd، d MMMM yyyy']]);date.setCurrentText(self._setting_get('date_format','dd/MM/yyyy'));time=SearchableCombo([(x,x) for x in ['HH:mm','HH:mm:ss','hh:mm AP','hh:mm:ss AP','HH:mm — 24 ساعة','hh:mm — 12 ساعة']]);time.setCurrentText(self._setting_get('time_format','HH:mm'));self._add_save(l,[('تنسيق التاريخ',date,'date_format'),('تنسيق الوقت',time,'time_format')]);self.stack.addWidget(p)
        p,l=self.page('الطباعة والطابعة');printers=[('الطابعة الافتراضية','default')]+[(x.printerName(),x.printerName()) for x in QPrinterInfo.availablePrinters()];printer=SearchableCombo(printers);printer.setCurrentData(self._setting_get('printer_name','default'));papers=['A4','A5','A6','A3','A2','A1','A0','Letter','Legal','Executive','B5','C5','DL','80mm رول حراري','58mm رول حراري','76mm رول حراري'];paper=SearchableCombo([(x,x) for x in papers]);paper.setCurrentData(self._setting_get('paper_size','A4'));self._add_save(l,[('الطابعة — اكتب جزءًا من الاسم للبحث',printer,'printer_name'),('مقاس الورق — جميع المقاسات الشائعة',paper,'paper_size')]);self.stack.addWidget(p)
        p,l=self.page('قالب الفاتورة والشعار');template=SearchableCombo([(x,x) for x in ['فاتورة تجارية كاملة','فاتورة سوبرماركت حرارية 80mm','فاتورة حرارية 58mm','فاتورة A4 رسمية','فاتورة ضريبية A4','فاتورة بيع مختصرة','فاتورة شراء','إشعار مرتجع بيع','إشعار مرتجع شراء']]);template.setCurrentData(self._setting_get('invoice_template','فاتورة تجارية كاملة'));logo=QLineEdit(self._setting_get('logo_path',''));pick=QPushButton('اختيار الشعار…');pick.clicked.connect(lambda:self.pick_logo(logo));row=QHBoxLayout();row.addWidget(logo,1);row.addWidget(pick);l.addRow('مسار الشعار',row);self._add_save(l,[('قالب الفاتورة — معالج بحث',template,'invoice_template')]);self.stack.addWidget(p)
        p,l=self.page('الأمان');l.addWidget(QLabel('الصلاحيات لا تمنع التنقل وفق سياسة التشغيل الحالية، مع بقاء التدقيق والعمليات المحاسبية محفوظة.'));self.stack.addWidget(p)
