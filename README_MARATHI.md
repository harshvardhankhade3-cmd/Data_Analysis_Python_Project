# Google Sheet Live Dashboard (मराठी सूचना)

Client Google Sheet मध्ये data भरतो. Program तो sheet ठरावीक वेळाने वाचतो, MySQL मध्ये ठेवतो आणि dashboard अपडेट करतो.

## Sheet कशी तयार करायची

1. Google Sheet उघडा. पहिल्या row मध्ये **हे** column नावे अगदी अशीच लिहा:

| student_name | city | batch | subject | marks | attendance_pct | exam_date |
|---|---|---|---|---|---|---|
| Aarav Patil | Pune | 2025-A | Math | 72 | 88 | 2026-03-01 |

   - `marks` 0 ते 100 मध्ये असावे.
   - `attendance_pct` 0 ते 100 मध्ये असावे.
   - `exam_date` तारीख स्वरूपात असावी (2026-03-01).

2. **Share** बटन दाबा. **General access** मध्ये **Anyone with the link** आणि **Viewer** निवडा. हे केले नाही तर program sheet वाचू शकणार नाही.

3. Sheet च्या URL मधून ID कॉपी करा. Example:
   `https://docs.google.com/spreadsheets/d/1AbC...XyZ/edit`
   यातला `/d/` आणि `/edit` मधला भाग (1AbC...XyZ) घ्या.

## Program सेटअप

1. `config.py` उघडा आणि `SHEET_ID` मध्ये तो ID टाका.
   ```
   SHEET_ID = "1AbC...XyZ"
   ```
2. XAMPP मध्ये **MySQL** Start करा.
3. Command Prompt मध्ये:
   ```
   cd C:\client_sheet_dashboard
   py -3.11 -m pip install -r requirements.txt
   py -3.11 sheet_dashboard.py
   ```
4. Chrome मध्ये `C:\client_sheet_dashboard\reports\dashboard.html` उघडा.

Window बंद करू नका. Ctrl+C दाबला की program थांबतो.

## Data बदलला तर काय होते

- Client ने sheet मध्ये बदल केला की पुढच्या cycle ला (`config.py` मधील `REFRESH_MINUTES`, सध्या 2 मिनिटे) dashboard आपोआप बदलतो.
- Dashboard page सुद्धा तितक्याच वेळाने आपोआप refresh होतो.
- Row हटवली तर ती dashboard वरून सुद्धा जाते, कारण दर वेळी पूर्ण data नव्याने घेतला जातो.
- Sheet वरचा बदल लगेच दिसत नाही. जास्तीत जास्त एक cycle वेळ लागतो.

## Dashboard वर काय दिसते

- Banner: शेवटचा sync यशस्वी झाला की हिरवा, नाही तर लाल (कारण सांगितलेले असते).
- KPI cards: students, average marks, pass % (40+), average attendance.
- Charts: vishay, batch, city, grade नुसार average; attendance vs marks.

## अडचणी

- **"Sheet public nahi"**: Share मध्ये "Anyone with the link" करा.
- **"Sheet madhe ya column names nahit"**: Header row ची नावे वर दिलेल्या नावांशी जुळत नाहीत. Client ने नाव बदलले तर हा error येतो, पण आधीचा data दिसत राहतो.
- **"MySQL madhe data nahi"**: XAMPP मध्ये MySQL सुरू आहे का तपासा.
- **"SHEET_ID takla nahi"**: `config.py` मध्ये `SHEET_ID` बदललेला नाही.

## phpMyAdmin मध्ये तपासणे

`client_results` database निवडा. `sql/queries.sql` मधल्या queries चालवून sheet मधला data आणि summary तपासा.
