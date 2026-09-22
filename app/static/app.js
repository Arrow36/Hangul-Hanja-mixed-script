const conversionGate = new RequestGate();
const sidebarGate = new RequestGate();
const selectionGate = new RequestGate();
const rawGate = new RequestGate();

const state = {
    inputText: '',
    segments: [],
    requestId: 0,
    inputRevision: 0,
    latestRequestId: 0,
    showEtymology: false,
    showSpaces: true,
    showHighlight: localStorage.getItem('ui-highlight') !== 'false',
    layoutMode: 'aligned', // 'aligned', 'mixed', or 'original'
    selectedSegmentId: null,
    sidebarEntry: null,
    sidebarSegment: null,
    lastSearchResults: null,
    lastProcessingMs: null,
    debounceTimer: null,
    isComposing: false,
    sidebarOpen: false,
    sidebarClosed: false,
    currentRequestedEntryId: null,
    entryRequestCounter: 0,
    dictDataDate: null,
    language: LanguageRoutes.initialLanguage()
};

const UI = {
    zh: {
        etym: '词源', split: '注音', aligned: '对照', copy: '复制', clear: '清空',
        showSpaces: '显示空格', hideSpaces: '隐藏空格', highlight: '突出显示',
        ready: '就绪', converting: '转换中…', done: '转换完成', error: '转换失败',
        chars: '个字符', placeholder: '输入或粘贴韩语文本……',
        empty: '输入韩语文本后，汉谚混写结果会显示在这里。',
        dictionary: '词典搜索与详情', search: '搜索', searchPlaceholder: '搜索词典……',
        searchWord: '词条', searchOrigin: '原语', searchId: 'ID',
        word: '词条', origin: '原语', processing: '处理时间',
        definitions: '释义', examples: '例句', candidates: '候选选择',
        details: '查看完整原始数据', copied: '已复制', selected: '已选择',
        originalText: '原文', mixedText: '汉谚混写',
        legendConverted: '橙色：已可靠转换', legendAmbiguous: '蓝色：存在歧义，需选择候选',
        jsonData: 'JSON 词典数据',
        noTranslationNotice: '（暂无中文释义，显示韩语原文）',
        dateUpdated: d => `JSON 词典数据 更新于${d}`,
        dateUnknown: 'JSON 词典数据（日期未知）',
        dataShort: '数据', charsShort: n => `${n}字`,
        statusShort: { ready: '就绪', done: '完成', converting: '转换中…', error: '失败' },
        modalTitle: '信息与说明', modalLegend: '图例说明', modalDict: '词典数据', modalTime: '处理耗时', modalAbout: '关于项目', modalDownload: '前往国立国语院下载页面 ↗'
    },
    ko: {
        etym: '어원', split: '주음', aligned: '대조', copy: '복사', clear: '지우기',
        showSpaces: '공백 표시', hideSpaces: '공백 숨기기', highlight: '강조 표시',
        ready: '준비', converting: '변환 중…', done: '변환 완료', error: '변환 오류',
        chars: '자', placeholder: '한국어 텍스트를 입력하거나 붙여넣으세요……',
        empty: '한국어를 입력하면 한자·한글 혼용 결과가 표시됩니다.',
        dictionary: '사전 검색 및 상세', search: '검색', searchPlaceholder: '사전 검색……',
        searchWord: '표제어', searchOrigin: '원어', searchId: 'ID',
        word: '표제어', origin: '원어', processing: '처리 시간',
        definitions: '뜻풀이', examples: '용례', candidates: '후보 선택',
        details: '전체 원본 데이터 보기', copied: '복사되었습니다', selected: '선택됨',
        originalText: '원문', mixedText: '한자·한글 혼용',
        legendConverted: '주황색: 신뢰할 수 있는 변환', legendAmbiguous: '파란색: 중의적이며 후보 선택 필요',
        jsonData: 'JSON 사전 데이터',
        noTranslationNotice: '',
        dateUpdated: d => `JSON 사전 데이터 업데이트: ${d}`,
        dateUnknown: 'JSON 사전 데이터 (날짜 미상)',
        dataShort: '데이터', charsShort: n => `${n}자`,
        statusShort: { ready: '준비', done: '완료', converting: '변환 중…', error: '오류' },
        modalTitle: '정보 및 안내', modalLegend: '범례 안내', modalDict: '사전 데이터', modalTime: '처리 시간', modalAbout: '프로젝트 정보', modalDownload: '국립국어원 다운로드 페이지로 이동 ↗'
    },
    en: {
        etym: 'Etymology', split: 'Reading', aligned: 'Aligned', copy: 'Copy', clear: 'Clear',
        showSpaces: 'Show spaces', hideSpaces: 'Hide spaces', highlight: 'Highlight',
        ready: 'Ready', converting: 'Converting…', done: 'Done', error: 'Error',
        chars: 'characters', placeholder: 'Enter or paste Korean text…',
        empty: 'Your Korean–Hanja mixed-script result will appear here.',
        dictionary: 'Dictionary', search: 'Search', searchPlaceholder: 'Search the dictionary…',
        searchWord: 'Word', searchOrigin: 'Origin', searchId: 'ID',
        word: 'Word', origin: 'Origin', processing: 'Processing time',
        definitions: 'Definitions', examples: 'Examples', candidates: 'Candidates',
        details: 'View full source data', copied: 'Copied', selected: 'Selected',
        originalText: 'Original', mixedText: 'Mixed script',
        legendConverted: 'Orange: reliable conversion', legendAmbiguous: 'Blue: ambiguous; choose a candidate',
        jsonData: 'JSON dictionary data',
        noTranslationNotice: '(No English translation available, showing Korean original)',
        dateUpdated: d => `JSON dictionary data updated ${d}`,
        dateUnknown: 'JSON dictionary data (date unknown)',
        dataShort: 'Data', charsShort: n => `${n} chars`,
        statusShort: { ready: 'Ready', done: 'Done', converting: 'Converting…', error: 'Error' },
        modalTitle: 'Information & Legend', modalLegend: 'Legend', modalDict: 'Dictionary Data', modalTime: 'Processing Time', modalAbout: 'About Project', modalDownload: 'Go to National Institute of Korean Language download ↗'
    },
    ja: {
        etym: '語源', split: '注音', aligned: '対照', copy: 'コピー', clear: '消去',
        showSpaces: '空白を表示', hideSpaces: '空白を隠す', highlight: '強調表示',
        ready: '準備完了', converting: '変換中…', done: '変換完了', error: '変換エラー',
        chars: '文字', placeholder: '韓国語の文章を入力または貼り付けてください……',
        empty: '漢字ハングル交じり文の結果がここに表示されます。',
        dictionary: '辞書検索・詳細', search: '検索', searchPlaceholder: '辞書を検索……',
        searchWord: '見出し語', searchOrigin: '原語', searchId: 'ID',
        word: '見出し語', origin: '原語', processing: '処理時間',
        definitions: '語義', examples: '用例', candidates: '候補選択',
        details: '原本データをすべて表示', copied: 'コピーしました', selected: '選択済み',
        originalText: '原文', mixedText: '漢字ハングル交じり',
        legendConverted: 'オレンジ：確実な変換', legendAmbiguous: '青：曖昧、候補選択が必要',
        jsonData: 'JSON辞書データ',
        noTranslationNotice: '（日本語訳がないため、韓国語原文を表示します）',
        dateUpdated: d => `JSON辞書データ 更新日：${d}`,
        dateUnknown: 'JSON辞書データ（日付不明）',
        dataShort: 'データ', charsShort: n => `${n}字`,
        statusShort: { ready: '準備', done: '完了', converting: '変換中…', error: 'エラー' },
        modalTitle: '情報と凡例', modalLegend: '凡例の説明', modalDict: '辞書データ', modalTime: '処理時間', modalAbout: 'プロジェクトについて', modalDownload: '国立国語院ダウンロードページへ ↗'
    },
    fr: {
        etym: 'Étymologie', split: 'Lecture', aligned: 'Aligné', copy: 'Copier', clear: 'Effacer',
        showSpaces: 'Afficher les espaces', hideSpaces: 'Masquer les espaces', highlight: 'Mise en valeur',
        ready: 'Prêt', converting: 'Conversion…', done: 'Terminé', error: 'Erreur',
        chars: 'caractères', placeholder: 'Saisissez ou collez un texte coréen…',
        empty: 'Le résultat mixte coréen–hanja apparaîtra ici.',
        dictionary: 'Dictionnaire', search: 'Rechercher', searchPlaceholder: 'Rechercher…',
        searchWord: 'Mot', searchOrigin: 'Origine', searchId: 'ID',
        word: 'Mot', origin: 'Origine', processing: 'Temps de traitement',
        definitions: 'Définitions', examples: 'Exemples', candidates: 'Candidats',
        details: 'Voir les données source', copied: 'Copié', selected: 'Sélectionné',
        originalText: 'Original', mixedText: 'Écriture mixte',
        legendConverted: 'Orange : conversion fiable', legendAmbiguous: 'Bleu : ambigu, choisir un candidat',
        jsonData: 'Données JSON du dictionnaire',
        noTranslationNotice: '(Aucune traduction française disponible, affichage du coréen original)',
        dateUpdated: d => `Données JSON du dictionnaire mis à jour le ${d}`,
        dateUnknown: 'Données JSON du dictionnaire (date inconnue)',
        dataShort: 'Données', charsShort: n => `${n} car.`,
        statusShort: { ready: 'Prêt', done: 'Terminé', converting: 'Conversion…', error: 'Erreur' },
        modalTitle: 'Informations et légende', modalLegend: 'Légende', modalDict: 'Données du dictionnaire', modalTime: 'Temps de traitement', modalAbout: 'À propos du projet', modalDownload: 'Aller sur la page de téléchargement ↗'
    },
    es: {
        etym: 'Etimología', split: 'Lectura', aligned: 'Alineado', copy: 'Copiar', clear: 'Borrar',
        showSpaces: 'Mostrar espacios', hideSpaces: 'Ocultar espacios', highlight: 'Resaltado',
        ready: 'Listo', converting: 'Convirtiendo…', done: 'Terminado', error: 'Error',
        chars: 'caracteres', placeholder: 'Escriba o pegue texto coreano…',
        empty: 'El resultado mixto coreano–hanja aparecerá aquí.',
        dictionary: 'Diccionario', search: 'Buscar', searchPlaceholder: 'Buscar…',
        searchWord: 'Palabra', searchOrigin: 'Origen', searchId: 'ID',
        word: 'Palabra', origin: 'Origen', processing: 'Tiempo de proceso',
        definitions: 'Definiciones', examples: 'Ejemplos', candidates: 'Candidatos',
        details: 'Ver datos originales', copied: 'Copiado', selected: 'Seleccionado',
        originalText: 'Original', mixedText: 'Escritura mixta',
        legendConverted: 'Naranja: conversión fiable', legendAmbiguous: 'Azul: ambiguo; elija un candidato',
        jsonData: 'Datos JSON del diccionario',
        noTranslationNotice: '(Sin traducción al español disponible, se muestra el original en coreano)',
        dateUpdated: d => `Datos JSON del diccionario actualizado el ${d}`,
        dateUnknown: 'Datos JSON del diccionario (fecha desconocida)',
        dataShort: 'Datos', charsShort: n => `${n} car.`,
        statusShort: { ready: 'Listo', done: 'Listo', converting: 'Convirtiendo…', error: 'Error' },
        modalTitle: 'Información y leyenda', modalLegend: 'Leyenda', modalDict: 'Datos del diccionario', modalTime: 'Tiempo de proceso', modalAbout: 'Acerca del proyecto', modalDownload: 'Ir a la página de descarga ↗'
    },
    ru: {
        etym: 'Этимология', split: 'Чтение', aligned: 'Сопоставить', copy: 'Копировать', clear: 'Очистить',
        showSpaces: 'Показать пробелы', hideSpaces: 'Скрыть пробелы', highlight: 'Выделение',
        ready: 'Готово', converting: 'Преобразование…', done: 'Завершено', error: 'Ошибка',
        chars: 'символов', placeholder: 'Введите или вставьте корейский текст…',
        empty: 'Здесь появится смешанный корейско-ханчовый текст.',
        dictionary: 'Словарь', search: 'Поиск', searchPlaceholder: 'Поиск в словаре…',
        searchWord: 'Слово', searchOrigin: 'Источник', searchId: 'ID',
        word: 'Слово', origin: 'Источник', processing: 'Время обработки',
        definitions: 'Значения', examples: 'Примеры', candidates: 'Варианты',
        details: 'Исходные данные', copied: 'Скопировано', selected: 'Выбрано',
        originalText: 'Исходный текст', mixedText: 'Смешанное письмо',
        legendConverted: 'Оранжевый: надёжное преобразование', legendAmbiguous: 'Синий: неоднозначно, выберите вариант',
        jsonData: 'Данные словаря JSON',
        noTranslationNotice: '(Перевод на русский отсутствует, показан оригинал на корейском)',
        dateUpdated: d => `Данные словаря JSON обновлено ${d}`,
        dateUnknown: 'Данные словаря JSON (дата неизвестна)',
        dataShort: 'Данные', charsShort: n => `${n} симв.`,
        statusShort: { ready: 'Готов', done: 'Готово', converting: 'Конвертация…', error: 'Ошибка' },
        modalTitle: 'Информация и обозначения', modalLegend: 'Обозначения', modalDict: 'Данные словаря', modalTime: 'Время обработки', modalAbout: 'О проекте', modalDownload: 'Перейти на страницу загрузки ↗'
    },
    vi: {
        etym: 'Từ nguyên', split: 'Phiên âm', aligned: 'Đối chiếu', copy: 'Sao chép', clear: 'Xóa',
        showSpaces: 'Hiện khoảng trắng', hideSpaces: 'Ẩn khoảng trắng', highlight: 'Làm nổi bật',
        ready: 'Sẵn sàng', converting: 'Đang chuyển đổi…', done: 'Hoàn tất', error: 'Lỗi',
        chars: 'ký tự', placeholder: 'Nhập hoặc dán văn bản tiếng Hàn…',
        empty: 'Kết quả hỗn hợp Hangul–Hanja sẽ xuất hiện tại đây.',
        dictionary: 'Từ điển', search: 'Tìm kiếm', searchPlaceholder: 'Tìm trong từ điển…',
        searchWord: 'Mục từ', searchOrigin: 'Từ nguyên', searchId: 'ID',
        word: 'Từ', origin: 'Từ nguyên', processing: 'Thời gian xử lý',
        definitions: 'Định nghĩa', examples: 'Ví dụ', candidates: 'Ứng viên',
        details: 'Xem dữ liệu gốc', copied: 'Đã sao chép', selected: 'Đã chọn',
        originalText: 'Nguyên văn', mixedText: 'Văn bản hỗn hợp',
        legendConverted: 'Cam: chuyển đổi đáng tin cậy', legendAmbiguous: 'Xanh: còn mơ hồ, cần chọn ứng viên',
        jsonData: 'Dữ liệu từ điển JSON',
        noTranslationNotice: '(Chưa có bản dịch tiếng Việt, hiển thị nguyên văn tiếng Hàn)',
        dateUpdated: d => `Dữ liệu từ điển JSON cập nhật ${d}`,
        dateUnknown: 'Dữ liệu từ điển JSON (không rõ ngày)',
        dataShort: 'Dữ liệu', charsShort: n => `${n} ký tự`,
        statusShort: { ready: 'Sẵn sàng', done: 'Xong', converting: 'Đang chuyển…', error: 'Lỗi' },
        modalTitle: 'Thông tin và chú giải', modalLegend: 'Chú giải', modalDict: 'Dữ liệu từ điển', modalTime: 'Thời gian xử lý', modalAbout: 'Về dự án', modalDownload: 'Đến trang tải xuống ↗'
    },
    mn: {
        etym: 'Үгийн гарал', split: 'Дуудлага', aligned: 'Зэрэгцүүлэх', copy: 'Хуулах', clear: 'Арилгах',
        showSpaces: 'Зайг харуулах', hideSpaces: 'Зайг нуух', highlight: 'Тодруулах',
        ready: 'Бэлэн', converting: 'Хөрвүүлж байна…', done: 'Дууссан', error: 'Алдаа гарлаа',
        chars: 'тэмдэгт', placeholder: 'Солонгос эх бичвэр оруулах эсвэл буулгах…',
        empty: 'Ханз-солонгос холимог бичвэрийн үр дүн энд гарна.',
        dictionary: 'Толь бичиг', search: 'Хайх', searchPlaceholder: 'Толиос хайх…',
        searchWord: 'Толгой үг', searchOrigin: 'Үгийн гарвал', searchId: 'ID',
        word: 'Үг', origin: 'Үгийн гарвал', processing: 'Боловсруулсан хугацаа',
        definitions: 'Тайлбар', examples: 'Жишээ', candidates: 'Сонголтууд',
        details: 'Эх өгөгдлийг бүрэн харах', copied: 'Хуулагдлаа', selected: 'Сонгогдсон',
        originalText: 'Эх бичвэр', mixedText: 'Холимог бичиг',
        legendConverted: 'Улбар шар: найдвартай хөрвүүлэгдсэн', legendAmbiguous: 'Цэнхэр: эргэлзээтэй, сонголт шаардлагатай',
        jsonData: 'JSON толь бичгийн өгөгдөл',
        noTranslationNotice: '(Монгол орчуулга байхгүй тул солонгос эх бичвэрийг харуулж байна)',
        dateUpdated: d => `JSON толь бичгийн өгөгдөл шинэчлэгдсэн ${d}`,
        dateUnknown: 'JSON толь бичгийн өгөгдөл (огноо тодорхойгүй)',
        dataShort: 'Өгөгдөл', charsShort: n => `${n} тэмдэгт`,
        statusShort: { ready: 'Бэлэн', done: 'Дууссан', converting: 'Хөрвүүлж байна…', error: 'Алдаа' },
        modalTitle: 'Мэдээлэл ба тайлбар', modalLegend: 'Тайлбар', modalDict: 'Толь бичгийн өгөгдөл', modalTime: 'Боловсруулсан хугацаа', modalAbout: 'Төслийн тухай', modalDownload: 'Татаж авах хуудас руу очих ↗'
    },
    ar: {
        etym: 'أصل الكلمة', split: 'النطق', aligned: 'محاذاة', copy: 'نسخ', clear: 'مسح',
        showSpaces: 'إظهار المسافات', hideSpaces: 'إخفاء المسافات', highlight: 'تمييز',
        ready: 'جاهز', converting: 'جارٍ التحويل…', done: 'اكتمل التحويل', error: 'فشل التحويل',
        chars: 'حرف', placeholder: 'أدخل أو الصق النص الكوري هنا…',
        empty: 'ستظهر نتيجة النص المختلط بين الهانجا والهانغول هنا.',
        dictionary: 'القاموس', search: 'بحث', searchPlaceholder: 'بحث في القاموس…',
        searchWord: 'المدخل', searchOrigin: 'الأصل', searchId: 'ID',
        word: 'كلمة', origin: 'الأصل', processing: 'وقت المعالجة',
        definitions: 'التعريفات', examples: 'أمثلة', candidates: 'الخيارات',
        details: 'عرض البيانات المصدرية الكاملة', copied: 'تم النسخ', selected: 'تم التحديد',
        originalText: 'النص الأصلي', mixedText: 'النص المختلط',
        legendConverted: 'برتقالي: تحويل موثوق', legendAmbiguous: 'أزرق: ملتبس، يتطلب اختيار مرشح',
        jsonData: 'بيانات القاموس بتنسيق JSON',
        noTranslationNotice: '(لا توجد ترجمة عربية متاحة، يتم عرض الأصل الكوري)',
        dateUpdated: d => `بيانات القاموس بتنسيق JSON تم التحديث في ${d}`,
        dateUnknown: 'بيانات القاموس بتنسيق JSON (تاريخ غير معروف)',
        dataShort: 'بيانات', charsShort: n => `${n} حرف`,
        statusShort: { ready: 'جاهز', done: 'اكتمل', converting: 'جارٍ التحويل…', error: 'خطأ' },
        modalTitle: 'المعلومات والدليل', modalLegend: 'دليل الألوان', modalDict: 'بيانات القاموس', modalTime: 'وقت المعالجة', modalAbout: 'حول المشروع', modalDownload: 'الانتقال إلى صفحة التنزيل ↗'
    },
    th: {
        etym: 'รากศัพท์', split: 'คำอ่าน', aligned: 'เทียบเคียง', copy: 'คัดลอก', clear: 'ล้าง',
        showSpaces: 'แสดงช่องว่าง', hideSpaces: 'ซ่อนช่องว่าง', highlight: 'ไฮไลต์',
        ready: 'พร้อม', converting: 'กำลังแปลง…', done: 'แปลงเสร็จสิ้น', error: 'เกิดข้อผิดพลาด',
        chars: 'ตัวอักษร', placeholder: 'พิมพ์หรือวางข้อความภาษาเกาหลี…',
        empty: 'ผลลัพธ์ตัวอักษรผสมฮันจา-ฮันกึลจะปรากฏที่นี่',
        dictionary: 'พจนานุกรม', search: 'ค้นหา', searchPlaceholder: 'ค้นหาในพจนานุกรม…',
        searchWord: 'คำศัพท์', searchOrigin: 'รากศัพท์เดิม', searchId: 'ID',
        word: 'คำศัพท์', origin: 'รากศัพท์เดิม', processing: 'เวลาประมวลผล',
        definitions: 'ความหมาย', examples: 'ตัวอย่าง', candidates: 'ตัวเลือกคำ',
        details: 'ดูข้อมูลต้นฉบับทั้งหมด', copied: 'คัดลอกแล้ว', selected: 'เลือกแล้ว',
        originalText: 'ข้อความต้นฉบับ', mixedText: 'อักษรผสม',
        legendConverted: 'สีส้ม: แปลงได้อย่างแม่นยำ', legendAmbiguous: 'สีฟ้า: มีความกำกวม โปรดเลือกตัวเลือก',
        jsonData: 'ข้อมูลพจนานุกรม JSON',
        noTranslationNotice: '(ไม่มีคำแปลภาษาไทย แสดงข้อความภาษาเกาหลีต้นฉบับ)',
        dateUpdated: d => `ข้อมูลพจนานุกรม JSON อัปเดตเมื่อ ${d}`,
        dateUnknown: 'ข้อมูลพจนานุกรม JSON (ไม่ระบุวันที่)',
        dataShort: 'ข้อมูล', charsShort: n => `${n} ตัว`,
        statusShort: { ready: 'พร้อม', done: 'เสร็จสิ้น', converting: 'กำลังแปลง…', error: 'ผิดพลาด' },
        modalTitle: 'ข้อมูลและคำอธิบาย', modalLegend: 'คำอธิบายสัญลักษณ์', modalDict: 'ข้อมูลพจนานุกรม', modalTime: 'เวลาประมวลผล', modalAbout: 'เกี่ยวกับโครงการ', modalDownload: 'ไปยังหน้าดาวน์โหลด ↗'
    },
    id: {
        etym: 'Etimologi', split: 'Pelafalan', aligned: 'Sejajar', copy: 'Salin', clear: 'Hapus',
        showSpaces: 'Tampilkan spasi', hideSpaces: 'Sembunyikan spasi', highlight: 'Sorotan',
        ready: 'Siap', converting: 'Mengonversi…', done: 'Selesai', error: 'Gagal',
        chars: 'karakter', placeholder: 'Masukkan atau tempel teks Korea…',
        empty: 'Hasil tulisan campuran Hangul–Hanja akan muncul di sini.',
        dictionary: 'Kamus', search: 'Cari', searchPlaceholder: 'Cari di kamus…',
        searchWord: 'Entri kata', searchOrigin: 'Asal kata', searchId: 'ID',
        word: 'Kata', origin: 'Asal kata', processing: 'Waktu pemrosesan',
        definitions: 'Definisi', examples: 'Contoh', candidates: 'Kandidat',
        details: 'Lihat data sumber lengkap', copied: 'Tersalin', selected: 'Terpilih',
        originalText: 'Teks asli', mixedText: 'Tulisan campuran',
        legendConverted: 'Oranye: konversi andal', legendAmbiguous: 'Biru: ambigu, pilih salah satu',
        jsonData: 'Data kamus JSON',
        noTranslationNotice: '(Terjemahan bahasa Indonesia belum tersedia, menampilkan teks asli Korea)',
        dateUpdated: d => `Data kamus JSON diperbarui ${d}`,
        dateUnknown: 'Data kamus JSON (tanggal tidak diketahui)',
        dataShort: 'Data', charsShort: n => `${n} kar.`,
        statusShort: { ready: 'Siap', done: 'Selesai', converting: 'Mengonversi…', error: 'Gagal' },
        modalTitle: 'Informasi & Legenda', modalLegend: 'Legenda', modalDict: 'Data Kamus', modalTime: 'Waktu Pemrosesan', modalAbout: 'Tentang Proyek', modalDownload: 'Buka halaman unduh ↗'
    }
};

const DICTIONARY_LANGUAGE = {
    zh: '중국어', ko: null, en: '영어', ja: '일본어',
    fr: '프랑스어', es: '스페인어', ru: '러시아어', vi: '베트남어',
    mn: '몽골어', ar: '아랍어', th: '타이어', id: '인도네시아어'
};

const MESSAGES = {
    zh: { loading: '加载中…', searching: '搜索中…', searchFailed: '搜索失败', noResults: '没有搜索结果', results: '搜索结果', reference: '参考', guide: '点击正文中的词语，或使用上方搜索框查询词典。', koreanDefinition: '韩语释义', koreanExamples: '韩语例句' },
    ko: { loading: '불러오는 중…', searching: '검색 중…', searchFailed: '검색 실패', noResults: '검색 결과가 없습니다', results: '검색 결과', reference: '참고', guide: '본문의 단어를 클릭하거나 위 검색창에서 사전을 검색하세요.', koreanDefinition: '한국어 뜻풀이', koreanExamples: '한국어 용례' },
    en: { loading: 'Loading…', searching: 'Searching…', searchFailed: 'Search failed', noResults: 'No results', results: 'Search results', reference: 'Note', guide: 'Click a word in the text or search the dictionary above.', koreanDefinition: 'Korean definition', koreanExamples: 'Korean examples' },
    ja: { loading: '読み込み中…', searching: '検索中…', searchFailed: '検索失敗', noResults: '検索結果がありません', results: '検索結果', reference: '参考', guide: '本文の語をクリックするか、上の欄で辞書を検索してください。', koreanDefinition: '韓国語の語義', koreanExamples: '韓国語の用例' },
    fr: { loading: 'Chargement…', searching: 'Recherche…', searchFailed: 'Échec de la recherche', noResults: 'Aucun résultat', results: 'Résultats', reference: 'Note', guide: 'Cliquez sur un mot du texte ou recherchez-le ci-dessus.', koreanDefinition: 'Définition coréenne', koreanExamples: 'Exemples coréens' },
    es: { loading: 'Cargando…', searching: 'Buscando…', searchFailed: 'Error de búsqueda', noResults: 'Sin resultados', results: 'Resultados', reference: 'Nota', guide: 'Pulse una palabra del texto o búsquela arriba.', koreanDefinition: 'Definición coreana', koreanExamples: 'Ejemplos coreanos' },
    ru: { loading: 'Загрузка…', searching: 'Поиск…', searchFailed: 'Ошибка поиска', noResults: 'Нет результатов', results: 'Результаты', reference: 'Примечание', guide: 'Нажмите слово в тексте или найдите его выше.', koreanDefinition: 'Определение на корейском', koreanExamples: 'Корейские примеры' },
    vi: { loading: 'Đang tải…', searching: 'Đang tìm…', searchFailed: 'Tìm kiếm thất bại', noResults: 'Không có kết quả', results: 'Kết quả', reference: 'Ghi chú', guide: 'Nhấp vào một từ trong văn bản hoặc tìm kiếm ở trên.', koreanDefinition: 'Định nghĩa tiếng Hàn', koreanExamples: 'Ví dụ tiếng Hàn' },
    mn: { loading: 'Ачаалж байна…', searching: 'Хайж байна…', searchFailed: 'Хайлт амжилтгүй', noResults: 'Илэрц олдсонгүй', results: 'Хайлтын үр дүн', reference: 'Тэмдэглэл', guide: 'Эх бичвэр дэх үгийг товших эсвэл дээрх талбараас толь бичгээс хайна уу.', koreanDefinition: 'Солонгос тайлбар', koreanExamples: 'Солонгос жишээ' },
    ar: { loading: 'جارٍ التحميل…', searching: 'جارٍ البحث…', searchFailed: 'فشل البحث', noResults: 'لا توجد نتائج', results: 'نتائج البحث', reference: 'ملاحظة', guide: 'انقر فوق كلمة في النص أو ابحث في القاموس أعلاه.', koreanDefinition: 'التعريف الكوري', koreanExamples: 'أمثلة كورية' },
    th: { loading: 'กำลังโหลด…', searching: 'กำลังค้นหา…', searchFailed: 'การค้นหาล้มเหลว', noResults: 'ไม่พบผลลัพธ์', results: 'ผลการค้นหา', reference: 'หมายเหตุ', guide: 'คลิกที่คำในข้อความหรือค้นหาในช่องค้นหาด้านบน', koreanDefinition: 'คำจำกัดความภาษาเกาหลี', koreanExamples: 'ตัวอย่างภาษาเกาหลี' },
    id: { loading: 'Memuat…', searching: 'Mencari…', searchFailed: 'Pencarian gagal', noResults: 'Tidak ada hasil', results: 'Hasil pencarian', reference: 'Catatan', guide: 'Klik kata dalam teks atau cari kamus di atas.', koreanDefinition: 'Definisi bahasa Korea', koreanExamples: 'Contoh bahasa Korea' }
};

const EXAMPLE_LABELS = {
    zh: { phrase: '短语', sentence: '例句', dialogue: '对话' },
    ko: { phrase: '구', sentence: '문장', dialogue: '대화' },
    en: { phrase: 'Phrases', sentence: 'Sentences', dialogue: 'Dialogue' },
    ja: { phrase: '句', sentence: '例文', dialogue: '対話' },
    fr: { phrase: 'Locutions', sentence: 'Phrases', dialogue: 'Dialogue' },
    es: { phrase: 'Frases breves', sentence: 'Ejemplos', dialogue: 'Diálogo' },
    ru: { phrase: 'Сочетания', sentence: 'Примеры', dialogue: 'Диалог' },
    vi: { phrase: 'Cụm từ', sentence: 'Câu ví dụ', dialogue: 'Hội thoại' },
    mn: { phrase: 'Хэллэг', sentence: 'Жишээ өгүүлбэр', dialogue: 'Харилцан яриа' },
    ar: { phrase: 'عبارات', sentence: 'جمل توضيحية', dialogue: 'حوار' },
    th: { phrase: 'วลี', sentence: 'ประโยคตัวอย่าง', dialogue: 'บทสนทนา' },
    id: { phrase: 'Frasa', sentence: 'Kalimat contoh', dialogue: 'Percakapan' }
};

const META_LABELS = {
    zh: { id: '词条 ID', unit: '词汇类型', semantic: '语义分类', subject: '主题分类', word: '单词' },
    ko: { id: '표제어 ID', unit: '어휘 유형', semantic: '의미 범주', subject: '주제 분류', word: '단어' },
    en: { id: 'Entry ID', unit: 'Lexical type', semantic: 'Semantic category', subject: 'Subject category', word: 'Word' },
    ja: { id: '項目 ID', unit: '語彙タイプ', semantic: '意味分類', subject: '主題分類', word: '単語' },
    fr: { id: 'ID de l’entrée', unit: 'Type lexical', semantic: 'Catégorie sémantique', subject: 'Catégorie thématique', word: 'Mot' },
    es: { id: 'ID de entrada', unit: 'Tipo léxico', semantic: 'Categoría semántica', subject: 'Categoría temática', word: 'Palabra' },
    ru: { id: 'ID статьи', unit: 'Тип лексики', semantic: 'Семантическая категория', subject: 'Тематическая категория', word: 'Слово' },
    vi: { id: 'ID mục từ', unit: 'Loại từ vựng', semantic: 'Phân loại ngữ nghĩa', subject: 'Phân loại chủ đề', word: 'Từ' },
    mn: { id: 'Бичлэгийн ID', unit: 'Үгийн төрөл', semantic: 'Утгын ангилал', subject: 'Сэдвийн ангилал', word: 'Үг' },
    ar: { id: 'معرّف المدخل', unit: 'النوع المعجمي', semantic: 'التصنيف الدلالي', subject: 'تصنيف الموضوع', word: 'كلمة' },
    th: { id: 'รหัสรายการ', unit: 'ประเภทคำศัพท์', semantic: 'หมวดความหมาย', subject: 'หมวดหัวข้อ', word: 'คำ' },
    id: { id: 'ID entri', unit: 'Jenis leksikal', semantic: 'Kategori semantik', subject: 'Kategori subjek', word: 'Kata' }
};

const t = key => (UI[state.language] || UI.zh)[key] ?? UI.zh[key] ?? '';
const m = key => (MESSAGES[state.language] || MESSAGES.zh)[key] ?? MESSAGES.zh[key] ?? '';

const localizePOS = value => {
    if (window.categoryI18n) return window.categoryI18n.localizePOS(value, state.language);
    return value;
};

const localizeLevel = value => {
    if (window.categoryI18n) return window.categoryI18n.localizeLevel(value, state.language);
    return value;
};

const preferredEquivalent = sense => {
    const language = DICTIONARY_LANGUAGE[state.language];
    return language ? (sense.equivalents || []).find(eq => eq.language === language) : null;
};

// DOM Elements
const elInput = document.getElementById('text-input');
const elResult = document.getElementById('result-area');
const elCharCount = document.getElementById('char-count');
const elStatus = document.getElementById('convert-status');
const elSidebar = document.getElementById('sidebar');
const elSidebarContent = document.getElementById('sidebar-content');
const elProcTime = document.getElementById('proc-time');

// Buttons & Inputs
const btnEtym = document.getElementById('btn-etym');
const btnLayout = document.getElementById('btn-layout');
const btnCopy = document.getElementById('btn-copy');
const btnClear = document.getElementById('btn-clear');
const btnShowSpaces = document.getElementById('btn-show-spaces');
const btnHighlight = document.getElementById('btn-highlight');
const btnCloseSidebar = document.getElementById('btn-close-sidebar');
const btnSearch = document.getElementById('btn-search');
const inputSearch = document.getElementById('search-input');
const selectSearch = document.getElementById('search-type');
const selectLanguage = document.getElementById('language-select');

function updateLayoutButton() {
    btnLayout.querySelectorAll('.mode-option').forEach(el => {
        el.textContent = el.dataset.mode === 'aligned' ? t('split') : (el.dataset.mode === 'mixed' ? t('mixedText') : t('originalText'));
        el.classList.toggle('active', el.dataset.mode === state.layoutMode);
    });
}

function updateHighlightState() {
    btnHighlight.textContent = t('highlight');
    btnHighlight.setAttribute('aria-pressed', String(state.showHighlight));
    btnHighlight.classList.toggle('active-on', state.showHighlight);
    btnHighlight.classList.toggle('highlight-off', !state.showHighlight);
    elResult.classList.toggle('highlight-off', !state.showHighlight);
}

function updateFooterDictDate() {
    const link = document.getElementById('dictionary-json-link');
    if (!link) return;
    if (window.innerWidth <= 768) {
        link.textContent = (UI[state.language] || UI.zh).dataShort || UI.zh.dataShort || '数据';
        return;
    }
    if (state.dictDataDate) {
        const tmpl = (UI[state.language] || UI.zh).dateUpdated || UI.zh.dateUpdated;
        link.textContent = typeof tmpl === 'function' ? tmpl(state.dictDataDate) : String(tmpl).replace('{date}', state.dictDataDate);
    } else {
        link.textContent = (UI[state.language] || UI.zh).dateUnknown || UI.zh.dateUnknown;
    }
}

function updateModalTexts() {
    const lang = state.language;
    const ui = UI[lang] || UI.zh;
    const setTxt = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };
    setTxt('modal-title', ui.modalTitle || '信息与说明');
    setTxt('modal-legend-title', ui.modalLegend || '图例说明');
    setTxt('modal-dict-title', ui.modalDict || '词典数据');
    setTxt('modal-time-title', ui.modalTime || '处理耗时');
    setTxt('modal-author-title', ui.modalAbout || '关于项目');
    setTxt('modal-dict-link', ui.modalDownload || '前往国立国语院下载页面 ↗');
    setTxt('modal-legend-converted', ui.legendConverted || '橙色：已可靠转换');
    setTxt('modal-legend-ambiguous', ui.legendAmbiguous || '蓝色：存在歧义，需选择候选');

    const modalDictDate = document.getElementById('modal-dict-date');
    if (modalDictDate) {
        if (state.dictDataDate) {
            const tmpl = ui.dateUpdated || UI.zh.dateUpdated;
            modalDictDate.textContent = typeof tmpl === 'function' ? tmpl(state.dictDataDate) : String(tmpl).replace('{date}', state.dictDataDate);
        } else {
            modalDictDate.textContent = ui.dateUnknown || UI.zh.dateUnknown;
        }
    }
}

function updateFooterStats() {
    const isMobile = window.innerWidth <= 768;
    const lang = state.language;
    const len = state.inputText.length;
    const hasResult = state.segments && state.segments.length > 0;
    const statusKey = hasResult ? 'done' : 'ready';

    if (isMobile) {
        const compactChars = (UI[lang] || UI.zh).charsShort || UI.zh.charsShort || (n => `${n}字`);
        elCharCount.textContent = typeof compactChars === 'function' ? compactChars(len) : `${len} ${compactChars}`;

        const compactStatus = (UI[lang] || UI.zh).statusShort || UI.zh.statusShort || {};
        elStatus.textContent = compactStatus[statusKey] || t(statusKey);

        elProcTime.textContent = state.lastProcessingMs != null ? `${state.lastProcessingMs}ms` : '—';

        const dictLink = document.getElementById('dictionary-json-link');
        if (dictLink) {
            dictLink.textContent = (UI[lang] || UI.zh).dataShort || UI.zh.dataShort || '数据';
        }
    } else {
        elCharCount.textContent = `${len} ${t('chars')}`;
        elStatus.textContent = t(statusKey);
        elProcTime.textContent = state.lastProcessingMs != null
            ? `${t('processing')}: ${state.lastProcessingMs} ms`
            : '—';
        updateFooterDictDate();
    }

    const modalTime = document.getElementById('modal-time-val');
    if (modalTime) {
        modalTime.textContent = state.lastProcessingMs != null ? `${state.lastProcessingMs} ms` : '—';
    }

    adjustFooterAndToolbarForSpace();
}

function adjustFooterAndToolbarForSpace() {
    const timeSep = document.querySelector('.footer-time-sep');
    const timeItem = document.querySelector('.footer-time-item');
    const footer = document.getElementById('main-footer');
    const toolbar = document.getElementById('result-toolbar');

    if (window.innerWidth > 768) {
        if (timeSep) timeSep.style.display = 'none';
        if (timeItem) timeItem.style.display = 'inline';
        if (toolbar) toolbar.classList.remove('toolbar-2x2');
        return;
    }

    const longLangs = ['ru', 'fr', 'es', 'vi', 'id', 'th', 'ar', 'mn'];
    if (toolbar) {
        if (window.innerWidth <= 360 || (longLangs.includes(state.language) && window.innerWidth <= 420)) {
            toolbar.classList.add('toolbar-2x2');
        } else {
            toolbar.classList.remove('toolbar-2x2');
        }
    }

    if (timeSep) timeSep.style.display = 'inline';
    if (timeItem) timeItem.style.display = 'inline';

    if (footer && footer.scrollWidth > footer.clientWidth) {
        if (timeSep) timeSep.style.display = 'none';
        if (timeItem) timeItem.style.display = 'none';
    }
}

async function fetchDictVersion() {
    try {
        const resp = await fetch('/api/version');
        if (resp.ok) {
            const data = await resp.json();
            if (data.data_version) {
                const matched = String(data.data_version).match(/(\d{4})[-_]?(\d{2})[-_]?(\d{2})/);
                if (matched) {
                    state.dictDataDate = `${matched[1]}_${matched[2]}_${matched[3]}`;
                }
            }
        }
    } catch (e) {
        console.warn('Failed to fetch dictionary version:', e);
    }
    updateFooterDictDate();
    updateModalTexts();
}

let lastFocusedElementBeforeModal = null;
function openInfoModal() {
    lastFocusedElementBeforeModal = document.activeElement;
    const modal = document.getElementById('info-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
    const closeBtn = document.getElementById('btn-close-modal');
    if (closeBtn) closeBtn.focus();
}

function closeInfoModal() {
    const modal = document.getElementById('info-modal');
    if (!modal) return;
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    if (lastFocusedElementBeforeModal && typeof lastFocusedElementBeforeModal.focus === 'function') {
        lastFocusedElementBeforeModal.focus();
    }
}

function applyLanguage() {
    document.documentElement.lang = state.language;
    document.title = '汉谚混写·국한문혼용체';
    selectLanguage.value = state.language;

    btnEtym.textContent = t('etym');
    updateLayoutButton();
    btnCopy.textContent = t('copy');
    btnClear.textContent = t('clear');
    btnShowSpaces.textContent = state.showSpaces ? t('hideSpaces') : t('showSpaces');
    updateHighlightState();

    // Example text is inserted as editable content during initialization
    elInput.placeholder = '';
    
    document.getElementById('sidebar-title').textContent = t('dictionary');
    inputSearch.placeholder = t('searchPlaceholder');
    btnSearch.textContent = t('search');

    if (selectSearch.options.length >= 3) {
        selectSearch.options[0].textContent = t('searchWord');
        selectSearch.options[1].textContent = t('searchOrigin');
        selectSearch.options[2].textContent = t('searchId');
    }

    document.getElementById('legend-converted').textContent = t('legendConverted');
    document.getElementById('legend-ambiguous').textContent = t('legendAmbiguous');
    updateFooterDictDate();
    updateModalTexts();
    updateFooterStats();

    const sidebarEmpty = document.getElementById('sidebar-empty');
    if (sidebarEmpty) sidebarEmpty.textContent = m('guide');

    renderResult();
    if (state.sidebarEntry && !state.sidebarClosed) {
        renderSidebar(state.sidebarSegment);
    } else if (state.lastSearchResults && !state.sidebarClosed) {
        renderSearchResults(state.lastSearchResults);
    }
}

selectLanguage.addEventListener('change', () => {
    state.language = selectLanguage.value;
    LanguageRoutes.navigate(state.language);
    applyLanguage();
});

window.addEventListener('popstate', () => {
    state.language = LanguageRoutes.fromPath() || LanguageRoutes.initialLanguage();
    LanguageRoutes.remember(state.language);
    applyLanguage();
});

const escapeHTML = (str) => {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
};

// Event Listeners
elInput.addEventListener('input', handleInput);
elInput.addEventListener('compositionstart', () => { state.isComposing = true; });
elInput.addEventListener('compositionend', (e) => {
    state.isComposing = false;
    handleInput(e);
});

btnEtym.addEventListener('click', () => {
    state.showEtymology = !state.showEtymology;
    btnEtym.classList.toggle('active', state.showEtymology);
    renderResult();
});

btnLayout.addEventListener('click', () => {
    const modes = ['aligned', 'mixed', 'original'];
    state.layoutMode = modes[(modes.indexOf(state.layoutMode) + 1) % modes.length];
    updateLayoutButton();
    renderResult();
});

// Space button: ONLY toggles text, NO class active, NO color change
btnShowSpaces.addEventListener('click', () => {
    state.showSpaces = !state.showSpaces;
    btnShowSpaces.textContent = state.showSpaces ? t('hideSpaces') : t('showSpaces');
    renderResult();
});

btnHighlight.addEventListener('click', () => {
    state.showHighlight = !state.showHighlight;
    localStorage.setItem('ui-highlight', state.showHighlight);
    updateHighlightState();
});

btnCopy.addEventListener('click', copyResult);

btnClear.addEventListener('click', () => {
    clearTimeout(state.debounceTimer);
    state.latestRequestId = `invalid-${++state.requestId}`;
    state.inputRevision++;
    conversionGate.cancel();
    selectionGate.cancel();
    sidebarGate.cancel();
    rawGate.cancel();
    state.sidebarSegment = null;
    if (state.sidebarEntry && !state.sidebarClosed) renderSidebar();
    elInput.value = '';
    state.inputText = '';
    state.segments = [];
    state.selectedSegmentId = null;
    state.lastProcessingMs = null;
    renderResult();
    updateFooterStats();
});

btnCloseSidebar.addEventListener('click', closeSidebar);

const btnInfoModal = document.getElementById('btn-info-modal');
if (btnInfoModal) btnInfoModal.addEventListener('click', openInfoModal);
const btnCloseModal = document.getElementById('btn-close-modal');
if (btnCloseModal) btnCloseModal.addEventListener('click', closeInfoModal);
const infoModal = document.getElementById('info-modal');
if (infoModal) {
    infoModal.addEventListener('click', (e) => {
        if (e.target.id === 'info-modal') closeInfoModal();
    });
}
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('info-modal');
        if (modal && modal.style.display !== 'none') {
            closeInfoModal();
        }
    }
});

btnSearch.addEventListener('click', () => {
    const query = inputSearch.value.trim();
    if (query) searchDictionary(query, selectSearch.value);
});

inputSearch.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const query = inputSearch.value.trim();
        if (query) searchDictionary(query, selectSearch.value);
    }
});

// Punctuation Detection: Strictly Unicode punctuation (\p{P}), excluding \p{S}
function isPunctuationSegment(seg) {
    if (!seg) return false;
    if (seg.is_punctuation) return true;
    const orig = (seg.original || '').trim();
    if (!orig) return false;
    return /^\p{P}+$/u.test(orig);
}

// Event Delegation for hover and click on segments
elResult.addEventListener('mouseover', (e) => {
    const segEl = e.target.closest('[data-segment-id]');
    if (!segEl) return;
    const segId = parseInt(segEl.dataset.segmentId, 10);
    const seg = state.segments.find(s => s.segment_id === segId);
    if (!seg || isPunctuationSegment(seg)) return;
    highlightSegments(segId, true);
});

elResult.addEventListener('mouseout', (e) => {
    const segEl = e.target.closest('[data-segment-id]');
    if (!segEl) return;
    const segId = parseInt(segEl.dataset.segmentId, 10);
    const seg = state.segments.find(s => s.segment_id === segId);
    if (!seg || isPunctuationSegment(seg)) return;
    highlightSegments(segId, false);
});

elResult.addEventListener('click', (e) => {
    const segEl = e.target.closest('[data-segment-id]');
    if (!segEl) return;
    const segId = parseInt(segEl.dataset.segmentId, 10);
    const seg = state.segments.find(s => s.segment_id === segId);
    if (!seg || isPunctuationSegment(seg)) return;

    selectSegment(segId);
    openSidebar();

    if (seg.matched_entry_id) {
        lookupEntry(seg.matched_entry_id, seg);
    } else if (seg.candidates && seg.candidates.length > 0) {
        lookupEntry(seg.candidates[0].entry_id, seg);
    } else {
        inputSearch.value = seg.original.trim();
        searchDictionary(seg.original.trim(), 'written_form');
    }
});

// Input & Conversion
function handleInput(e) {
    state.inputText = elInput.value;
    state.latestRequestId = `invalid-${++state.requestId}`;
    state.inputRevision++;
    conversionGate.cancel();
    selectionGate.cancel();
    sidebarGate.cancel();
    rawGate.cancel();
    state.sidebarSegment = null;
    if (state.sidebarEntry && !state.sidebarClosed) renderSidebar();
    clearTimeout(state.debounceTimer);

    if (!state.isComposing && state.inputText.trim().length > 0) {
        elStatus.textContent = t('converting');
        updateFooterStats();
        state.debounceTimer = setTimeout(() => {
            convertText(state.inputText);
        }, 350);
    } else if (state.inputText.trim().length === 0) {
        state.segments = [];
        state.lastProcessingMs = null;
        renderResult();
        updateFooterStats();
    }
}

async function convertText(text) {
    const request = conversionGate.begin();
    const reqId = `req-${++state.requestId}`;
    state.latestRequestId = reqId;
    const startTime = performance.now();

    try {
        const resp = await fetch('/api/convert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, request_id: reqId }),
            signal: request.signal
        });

        if (!resp.ok) throw new Error('Conversion failed');
        const data = await resp.json();

        if (!request.isCurrent() || data.request_id !== state.latestRequestId) return;

        state.segments = data.segments || [];
        const endTime = performance.now();
        state.lastProcessingMs = (endTime - startTime).toFixed(1);
        updateFooterStats();
        renderResult();
    } catch (error) {
        if (error.name === 'AbortError' || !request.isCurrent()) return;
        console.error('Conversion error:', error);
        if (reqId === state.latestRequestId) {
            elStatus.textContent = t('error');
            updateFooterStats();
        }
    }
}

async function lookupEntry(entryId, segmentData = null) {
    const request = sidebarGate.begin();
    rawGate.cancel();
    state.currentRequestedEntryId = entryId;
    openSidebar();
    try {
        elSidebarContent.textContent = m('loading');
        const resp = await fetch(`/api/entries/${entryId}`, { signal: request.signal });
        if (!resp.ok) throw new Error('Entry lookup failed');
        const data = await resp.json();
        if (!request.isCurrent() || state.sidebarClosed) return;
        state.sidebarEntry = data;
        state.sidebarSegment = segmentData;
        state.lastSearchResults = null;
        renderSidebar(segmentData);
    } catch (error) {
        if (!request.isCurrent() || state.sidebarClosed || error.name === 'AbortError') return;
        elSidebarContent.textContent = t('error');
    }
}

async function searchDictionary(query, searchType = 'written_form', page = 1) {
    const request = sidebarGate.begin();
    rawGate.cancel();
    state.currentRequestedEntryId = null;
    openSidebar();
    try {
        elSidebarContent.textContent = m('searching');
        const resp = await fetch(`/api/lookup?query=${encodeURIComponent(query)}&search_type=${encodeURIComponent(searchType)}&page=${page}&page_size=20`, { signal: request.signal });
        if (!resp.ok) throw new Error('Search failed');
        const data = await resp.json();
        if (!request.isCurrent() || state.sidebarClosed) return;
        state.lastSearchResults = data;
        state.sidebarEntry = null;
        state.sidebarSegment = null;
        renderSearchResults(data);
    } catch (error) {
        if (!request.isCurrent() || state.sidebarClosed || error.name === 'AbortError') return;
        state.lastSearchResults = null;
        elSidebarContent.textContent = m('searchFailed');
    }
}

async function applyCandidateChoice(segmentId, candidateIndex) {
    const seg = state.segments.find(s => s.segment_id === segmentId);
    const candidate = seg && (seg.candidates || [])[candidateIndex];
    if (!candidate) return;
    const request = selectionGate.begin();
    const revision = state.inputRevision;
    try {
        const resp = await fetch('/api/select-candidate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: request.signal,
            body: JSON.stringify({segment_id: segmentId, entry_id: candidate.entry_id, original: seg.original})
        });
        if (!resp.ok) throw new Error('Candidate selection failed');
        const data = await resp.json();
        if (!request.isCurrent() || revision !== state.inputRevision || !state.segments.includes(seg)) return;
        Object.assign(seg, {
            display_text: data.display_text, matched_entry_id: data.matched_entry_id,
            origin_raw: data.origin_raw, origin: data.origin,
            selection_reason: 'user_selected', status: data.is_reliable ? 'converted' : 'ambiguous'
        });
        renderResult();
        if (!state.sidebarClosed && state.selectedSegmentId === segmentId) lookupEntry(candidate.entry_id, seg);
    } catch (error) {
        if (!request.isCurrent() || error.name === 'AbortError') return;
        showToast(t('error'));
    }
}

async function loadRawEntry(button) {
    const entry = state.sidebarEntry;
    if (!entry) return;
    const request = rawGate.begin();
    button.disabled = true;
    try {
        const resp = await fetch(`/api/entries/${entry.id}/raw`, { signal: request.signal });
        if (!resp.ok) throw new Error('Raw entry lookup failed');
        const data = await resp.json();
        if (!request.isCurrent() || state.sidebarEntry !== entry || state.sidebarClosed) return;
        entry.raw_json = data;
        const pre = document.getElementById('raw-json');
        if (!pre) return;
        pre.textContent = JSON.stringify(data, null, 2);
        pre.style.display = 'block';
        button.style.display = 'none';
    } catch (error) {
        if (request.isCurrent() && error.name !== 'AbortError') showToast(t('error'));
    } finally {
        button.disabled = false;
    }
}

elSidebarContent.addEventListener('click', event => {
    const button = event.target.closest('[data-load-raw]');
    if (button) loadRawEntry(button);
});

// Rendering Functions
function getSegmentDisplayText(seg) {
    if (state.showEtymology) {
        if (seg.origin?.raw) return seg.origin.raw;
        const resolved = seg.status === 'converted' || seg.selection_reason === 'user_selected';
        if (resolved && seg.matched_entry_id && seg.origin_raw) return seg.origin_raw;
        if (seg.candidates?.length) {
            const origins = [...new Set(seg.candidates.map(c => c.origin_raw).filter(Boolean))];
            if (origins.length) return origins.join(' / ');
        }
    }
    return seg.display_text;
}

function renderWhitespace(text) {
    if (state.showSpaces) return escapeHTML(text);
    return escapeHTML(text.replace(/[ \t]+/g, ''));
}

function getSegmentClass(seg) {
    let cls = '';
    if (seg.selection_reason === 'user_selected') cls = 'seg-user-selected';
    else if (seg.status === 'converted') cls = 'seg-converted';
    else if (seg.status === 'ambiguous') cls = 'seg-ambiguous';
    else cls = 'seg-kept';

    if (seg.segment_id === state.selectedSegmentId) {
        cls += ' seg-selected';
    }
    return cls;
}

function renderResult() {
    elResult.classList.toggle('highlight-off', !state.showHighlight);

    if (!state.segments || state.segments.length === 0) {
        elResult.innerHTML = '';
        return;
    }

    if (state.layoutMode === 'aligned') {
        let html = '<div class="align-container">';
        state.segments.forEach(seg => {
            const display = getSegmentDisplayText(seg);
            const whitespaceOnly = /^\s+$/.test(seg.original);
            const isPunct = isPunctuationSegment(seg);
            const isKept = seg.status === 'kept';
            const hasDifferentDisplay = display !== seg.original;
            const cls = getSegmentClass(seg);

            if (whitespaceOnly) {
                html += `<span class="whitespace-segment">${renderWhitespace(seg.original)}</span>`;
            } else if (isPunct) {
                html += `<span class="align-single seg-punct">${renderWhitespace(seg.original)}</span>`;
            } else if (isKept && !hasDifferentDisplay) {
                html += `<span class="align-single ${cls}" data-segment-id="${seg.segment_id}" tabindex="0">${renderWhitespace(seg.original)}</span>`;
            } else {
                html += `
                <div class="align-pair ${cls}" data-segment-id="${seg.segment_id}" tabindex="0">
                    <div class="align-original">${renderWhitespace(seg.original)}</div>
                    <div class="align-result">${renderWhitespace(display)}</div>
                </div>`;
            }
        });
        html += '</div>';
        elResult.innerHTML = html;
    } else {
        const showOriginal = state.layoutMode === 'original';
        let htmlResult = `<div class="split-box"><div class="split-label">${escapeHTML(showOriginal ? t('originalText') : t('mixedText'))}</div><div class="split-text">`;
        state.segments.forEach(seg => {
            const display = getSegmentDisplayText(seg);
            const isPunct = isPunctuationSegment(seg);
            const cls = `seg ${getSegmentClass(seg)}`;
            const text = showOriginal ? seg.original : display;
            if (/^\s+$/.test(seg.original)) {
                htmlResult += `<span class="whitespace-segment">${renderWhitespace(text)}</span>`;
            } else if (isPunct) {
                htmlResult += `<span class="seg seg-kept seg-punct">${renderWhitespace(text)}</span>`;
            } else {
                htmlResult += `<span class="${cls}" data-segment-id="${seg.segment_id}" tabindex="0">${renderWhitespace(text)}</span>`;
            }
        });
        htmlResult += '</div></div>';
        elResult.innerHTML = `<div class="split-container">${htmlResult}</div>`;
    }
}

function renderSidebar(segmentData = null) {
    const entry = state.sidebarEntry;
    if (!entry) return;

    const safe = escapeHTML;
    let html = `<div class="entry-header">`;

    // Title and badges
    const posLocalized = localizePOS(entry.part_of_speech);
    const levelLocalized = localizeLevel(entry.vocabulary_level);

    html += `<div class="entry-title">${safe(entry.written_form)}`;
    if (entry.homonym_number) html += `<span class="homonym-badge" title="동음이의어 번호">${entry.homonym_number}</span>`;
    if (entry.part_of_speech) html += `<span class="pos-badge">${safe(posLocalized)}</span>`;
    if (entry.vocabulary_level) html += `<span class="level-badge">${safe(levelLocalized)}</span>`;
    html += `</div>`;

    // Meta chips with category translations
    const meta = META_LABELS[state.language] || META_LABELS.zh;
    html += `<div class="entry-meta-chips"><span class="entry-meta-chip">${safe(meta.id)}: ${entry.id}</span>`;
    if (entry.lexical_unit) {
        const unitTrans = window.categoryI18n ? window.categoryI18n.localizeLexicalUnit(entry.lexical_unit, state.language) : (entry.lexical_unit === '단어' ? meta.word : entry.lexical_unit);
        html += `<span class="entry-meta-chip">${safe(meta.unit)}: ${safe(unitTrans)}</span>`;
    }
    if (entry.semantic_category) {
        const semTrans = window.categoryI18n ? window.categoryI18n.localizeSemanticCategory(entry.semantic_category, state.language) : entry.semantic_category;
        html += `<span class="entry-meta-chip">${safe(meta.semantic)}: ${safe(semTrans)}</span>`;
    }
    if (entry.subject_category) {
        const subTrans = window.categoryI18n ? window.categoryI18n.localizeSubjectCategory(entry.subject_category, state.language) : entry.subject_category;
        html += `<span class="entry-meta-chip">${safe(meta.subject)}: ${safe(subTrans)}</span>`;
    }
    html += `</div>`;

    // Pronunciation & Sound
    const wfWithSound = (entry.word_forms || []).find(w => w.sound_url);
    const wfPron = (entry.word_forms || []).find(w => w.pronunciation);
    if (wfWithSound || wfPron) {
        html += `<div class="pronunciation-box">`;
        if (wfPron && wfPron.pronunciation) {
            html += `<span>[${safe(wfPron.pronunciation)}]</span>`;
        }
        if (wfWithSound && wfWithSound.sound_url) {
            html += `<button class="audio-btn" onclick="playAudio('${encodeURI(wfWithSound.sound_url)}')" title="발음 듣기">🔊</button>`;
        }
        html += `</div>`;
    }

    // Origin Box
    if (entry.origin_raw) {
        html += `
        <div class="origin-box">
            <div>
                <div class="origin-label">${safe(t('origin'))}</div>
                <strong>${safe(entry.origin_raw)}</strong>
            </div>
        </div>`;
    }
    html += `</div>`;

    // Candidates list if the user clicked a segment with choices
    if (segmentData && segmentData.candidates && segmentData.candidates.length > 0) {
        html += `<div class="candidates-section">`;
        html += `<h4>${safe(t('candidates'))}: "${safe(segmentData.original)}"</h4>`;

        segmentData.candidates.forEach((cand, idx) => {
            const isSelected = (segmentData.status === 'converted' || segmentData.selection_reason === 'user_selected') && segmentData.matched_entry_id === cand.entry_id;
            const candPOS = localizePOS(cand.part_of_speech);
            html += `
            <div class="candidate-card ${isSelected ? 'active' : ''}" onclick="applyCandidateChoice(${segmentData.segment_id}, ${idx})">
                <div>
                    <span class="candidate-hanja">${safe(cand.replacement || cand.origin_raw || cand.written_form)}</span>
                    ${cand.origin_raw ? `<span style="margin-left:6px; color:var(--text-muted)">(${safe(cand.origin_raw)})</span>` : ''}
                </div>
                <div class="candidate-meta">
                    ${cand.part_of_speech ? `<span>${safe(candPOS)}</span>` : ''}
                    ${isSelected ? ` <strong style="color:var(--primary)">✓ ${safe(t('selected'))}</strong>` : ''}
                </div>
            </div>`;
        });
        html += `</div>`;
    }

    // Senses List with language priority & fallback notice
    if (entry.senses && entry.senses.length > 0) {
        html += `<div style="margin-top:16px;">`;
        html += `<h4 style="font-size:0.95rem; margin-bottom:10px; color:var(--primary);">${safe(t('definitions'))}</h4>`;

        entry.senses.forEach((sense, idx) => {
            const preferred = preferredEquivalent(sense);
            let displayedDefinition = '';
            let hasNoTranslation = false;

            if (state.language === 'ko') {
                displayedDefinition = sense.definition;
            } else if (preferred && preferred.definition) {
                displayedDefinition = preferred.definition;
            } else {
                hasNoTranslation = true;
                displayedDefinition = sense.definition;
            }

            html += `<div class="sense-item">`;
            html += `<div class="sense-def"><span class="sense-num">${sense.sense_number || (idx + 1)}.</span> `;
            if (hasNoTranslation && t('noTranslationNotice')) {
                html += `<span class="no-translation-notice">${safe(t('noTranslationNotice'))} </span>`;
            }
            html += `${safe(displayedDefinition)}</div>`;

            if (preferred?.lemma) html += `<div class="sense-pattern">${safe(preferred.lemma)}</div>`;

            if (state.language === 'ko' && sense.syntactic_pattern) {
                html += `<div class="sense-pattern">${safe(sense.syntactic_pattern)}</div>`;
            }
            if (state.language === 'ko' && sense.annotation) {
                html += `<div style="font-size:0.82rem; color:#555; margin-bottom:4px;">${safe(m('reference'))}: ${safe(sense.annotation)}</div>`;
            }

            const examples = sense.examples || [];
            const phrases = examples.filter(ex => ex.example_type === '구');
            const sentences = examples.filter(ex => ex.example_type === '문장');
            const dialogues = examples.filter(ex => ex.example_type === '대화');
            const otherExamples = examples.filter(ex => ex.example_type !== '구' && ex.example_type !== '문장' && ex.example_type !== '대화');

            if (sense.definition || examples.length) {
                const labels = EXAMPLE_LABELS[state.language] || EXAMPLE_LABELS.zh;
                html += `<div class="korean-info-box">`;
                if (sense.definition) html += `<div class="korean-info-section"><div class="korean-info-title">${safe(m('koreanDefinition'))}</div>${safe(sense.definition)}</div>`;
                if (phrases.length) {
                    html += `<div class="korean-info-section"><div class="korean-info-title">${safe(labels.phrase)}</div><ul class="examples-list">`;
                    phrases.forEach(ex => { html += `<li>${safe(ex.example)}</li>`; });
                    html += `</ul></div>`;
                }
                if (sentences.length || otherExamples.length) {
                    html += `<div class="korean-info-section"><div class="korean-info-title">${safe(labels.sentence)}</div><ul class="examples-list">`;
                    sentences.concat(otherExamples).forEach(ex => { html += `<li>${safe(ex.example)}</li>`; });
                    html += `</ul></div>`;
                }
                if (dialogues.length) {
                    const dialogueGroups = new Map();
                    dialogues.forEach(ex => {
                        const gid = ex.group_index != null ? ex.group_index : `d_${Math.random()}`;
                        if (!dialogueGroups.has(gid)) dialogueGroups.set(gid, []);
                        dialogueGroups.get(gid).push(ex);
                    });

                    html += `<div class="korean-info-section"><div class="korean-info-title">${safe(labels.dialogue || '대화')}</div><div class="dialogues-container">`;
                    const speakers = ['가', '나', '다', '라', '마'];
                    dialogueGroups.forEach(group => {
                        group.sort((a, b) => (a.order_index ?? 0) - (b.order_index ?? 0));
                        html += `<div class="dialogue-card">`;
                        group.forEach((ex, sidx) => {
                            const speaker = speakers[sidx] || `${sidx + 1}`;
                            const hasSpeaker = /^[가-힣A-Za-z0-9]+:/.test(ex.example.trim());
                            html += `<div class="dialogue-line">${hasSpeaker ? '' : `<span class="dialogue-speaker">${safe(speaker)}:</span>`}${safe(ex.example)}</div>`;
                        });
                        html += `</div>`;
                    });
                    html += `</div></div>`;
                }
                html += `</div>`;
            }

            html += `</div>`;
        });
        html += `</div>`;
    }

    // Related Forms with relation type translation
    if (entry.related_forms && entry.related_forms.length > 0) {
        html += `<div style="margin-top:16px; font-size:0.85rem;">`;
        html += `<h4 style="font-size:0.9rem; margin-bottom:6px; color:var(--primary);">${safe(t('dictionary'))}</h4>`;
        html += `<div style="display:flex; flex-wrap:wrap; gap:6px;">`;
        entry.related_forms.forEach(rf => {
            const relLocalized = window.categoryI18n ? window.categoryI18n.localizeRelationType(rf.relation_type, state.language) : rf.relation_type;
            html += `<span style="background:#eee; padding:2px 8px; border-radius:4px; cursor:pointer;" onclick="searchDictionary('${safe(rf.written_form)}', 'written_form')">${safe(rf.written_form)} (${safe(relLocalized)})</span>`;
        });
        html += `</div></div>`;
    }

    // Raw JSON expandable
    html += `
        <div style="margin-top: 24px; text-align: center; border-top: 1px solid #eee; padding-top: 14px;">
            <button data-load-raw>${safe(t('details'))}</button>
            <pre id="raw-json" style="display:none; text-align:left; background:#f5f5f5; padding:10px; border-radius:4px; overflow-x:auto; font-size:0.75rem; margin-top:10px; max-height:300px;">${entry.raw_json ? safe(JSON.stringify(entry.raw_json, null, 2)) : ''}</pre>
        </div>
    `;

    elSidebarContent.innerHTML = html;
}

function renderSearchResults(data) {
    if (!data.results || data.results.length === 0) {
        elSidebarContent.innerHTML = `<div style="padding:30px; text-align:center; color:var(--text-muted)">${escapeHTML(m('noResults'))}</div>`;
        return;
    }

    let html = `<div style="margin-bottom:12px; font-size:0.88rem; color:var(--text-muted);">${escapeHTML(m('results'))}: <strong>${data.total}</strong></div>`;

    data.results.forEach(res => {
        const posTrans = localizePOS(res.part_of_speech);
        html += `
            <div class="search-result-item" onclick="lookupEntry(${res.id})">
                <div style="font-size: 1.15rem; font-family:'Noto Serif KR', serif; font-weight:600; color: var(--primary);">
                    ${escapeHTML(res.written_form)}
                    ${res.homonym_number ? `<span class="homonym-badge">${res.homonym_number}</span>` : ''}
                    ${res.part_of_speech ? `<span class="pos-badge">${escapeHTML(posTrans)}</span>` : ''}
                </div>
                ${res.origin_raw ? `<div style="font-family: 'Noto Serif KR', serif; color:#e65100; font-size:0.95rem; margin-top:2px;">${escapeHTML(res.origin_raw)}</div>` : ''}
                ${state.language === 'ko' ? `<div style="font-size:.85rem;color:var(--text-muted);margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHTML(res.definition_preview || '')}</div>` : ''}
            </div>
        `;
    });

    elSidebarContent.innerHTML = html;
}

// Audio Player with Error Handling
function playAudio(url) {
    try {
        const audio = new Audio(url);
        audio.play().catch(err => {
            console.warn('Audio playback failed:', err);
            showToast('음원 링크를 재생할 수 없습니다');
        });
    } catch (e) {
        showToast('오디오 재생을 지원하지 않습니다');
    }
}

// Highlight & Selection synchronization
function highlightSegments(segmentId, active) {
    const elements = document.querySelectorAll(`[data-segment-id="${segmentId}"]`);
    elements.forEach(el => {
        if (active) el.classList.add('seg-hover');
        else el.classList.remove('seg-hover');
    });
}

function selectSegment(segmentId) {
    if (state.selectedSegmentId !== null) {
        document.querySelectorAll(`[data-segment-id="${state.selectedSegmentId}"]`)
            .forEach(el => el.classList.remove('seg-selected'));
    }

    state.selectedSegmentId = segmentId;

    if (segmentId !== null) {
        document.querySelectorAll(`[data-segment-id="${segmentId}"]`)
            .forEach(el => el.classList.add('seg-selected'));
    }
}

function openSidebar() {
    state.sidebarClosed = false;
    state.sidebarOpen = true;
    elSidebar.classList.remove('closed');
    elSidebar.removeAttribute('aria-hidden');
    elSidebar.inert = false;
    if (window.innerWidth <= 768) {
        elSidebar.classList.add('open');
    }
}

function closeSidebar() {
    sidebarGate.cancel();
    rawGate.cancel();
    selectionGate.cancel();
    state.sidebarClosed = true;
    state.sidebarOpen = false;
    state.currentRequestedEntryId = null;
    elSidebar.classList.add('closed');
    elSidebar.classList.remove('open');
    elSidebar.setAttribute('aria-hidden', 'true');
    elSidebar.inert = true;
    selectSegment(null);
}

function copyResult() {
    const text = state.segments
        .map(s => getSegmentDisplayText(s))
        .join('');

    if (!text) {
        showToast('복사할 텍스트가 없습니다');
        return;
    }

    navigator.clipboard.writeText(text).then(() => {
        showToast(t('copied'));
    }).catch(err => {
        showToast('복사 실패');
    });
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 2200);
}

// Responsive handling
window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
        elSidebar.classList.remove('open');
    } else if (state.sidebarOpen && !state.sidebarClosed) {
        elSidebar.classList.add('open');
    }
    adjustFooterAndToolbarForSpace();
});

// Initialize editable example text and convert it immediately
window.addEventListener('DOMContentLoaded', () => {
    LanguageRoutes.remember(state.language);
    applyLanguage();
    fetchDictVersion();
    elInput.value = '나라의 말이 중국과 달라 문자와 서로 통하지 아니하므로';
    state.inputText = elInput.value;
    state.segments = [];
    state.lastProcessingMs = null;
    renderResult();
    elStatus.textContent = t('converting');
    updateFooterStats();
    convertText(state.inputText);
});
