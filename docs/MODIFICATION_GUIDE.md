# ATMACA Flight Analyzer – Değişiklik Rehberi (prova sayfası)

Bu sayfa sunuma hazırlık içindir. Jüri "şu limiti değiştirin", "şu grafiği ekleyin" gibi canlı değişiklikler
isteyecek. Aşağıdaki 15 alıştırmanın her biri **en fazla 2 dosyada, en fazla 10 satırla** yapılabiliyor ve her biri
projenin bir kopyasında denendi. Önce 1. bölümü (program nasıl çalışır) okuyun; o sayfa her dosyayı anlatmaya yeter.

## 0. Sunumda bir değişiklik nasıl yapılır

1. Uygulama açık kalsın: `streamlit run app.py`.
2. Dosyayı VS Code'da değiştirin ve kaydedin (Ctrl+S).
3. Tarayıcıda sağ üstte **"Source file changed"** çıkar → **Rerun** (veya **Always rerun**: sonraki kayıtlarda
   kendiliğinden yenilenir). Sayfa değişmezse F5.
4. Hata olursa sayfada kırmızı bir kutu çıkar; en alttaki satır dosya adını ve satır numarasını gösterir.
5. Sonra `pytest` çalıştırın. Değişikliği geri almak için: `git restore <dosya>`.

`loader.py` değiştirilirse, önceden yüklenmiş dosya önbellekten gelebilir: sağ üst menü (⋮) → **Clear cache**.

## 1. Program nasıl çalışır

### Veri akışı

```
dosya (.csv / .TXT / .BBL)
   │  loader.py   flights_in_file()  .TXT/.BBL ise blackbox_decode.exe ile bir kez çözülür (logs/decoded/)
   │              load_flight()      CSV → normalize DataFrame (0.1 s'de bir satır) + x_m, y_m, dist_m
   ▼
DataFrame ──► events.py   find_events(df, params)          → list[Event]   (ARM, MODE, RTH_START, …)
   │                                   │
   │                                   ▼
   ├────────► metrics.py  compute_metrics(df, events, params) → list[Metric] (SC-2 … SC-8)
   │          metrics.py  summary(df, params)                  → kartlar
   ▼
charts.py   harita, 6 zaman grafiği, kriter tablosu, olay tablosu
   ▼
app.py      sayfa: sadece fonksiyonları çağırır ve sonucu gösterir
```

### Dosyaların görevi

| Dosya | Ne yapar | Ne zaman açılır |
|---|---|---|
| `config.py` | **Bütün sabitler**: varsayılan parametreler, başarı limitleri, analiz kuralları, renkler, boyutlar, yollar, decoder sütun adları | Bir sayı, renk veya isim değişecekse |
| `models.py` | Üç veri kabı: `Params` (kenar çubuğundaki parametreler), `Event` (olay), `Metric` (tablo satırı) | Yeni bir alan gerekiyorsa |
| `loader.py` | Dosyayı okur; blackbox logunu çözer; sütunları dönüştürür; evi bulur | Gerçek log yüklenmiyorsa |
| `geo.py` | Derece ↔ metre çevirisi, harita için çember noktaları | Neredeyse hiç |
| `events.py` | Her olay türü için küçük bir dedektör; satırı bir öncekiyle karşılaştırır | Yeni olay |
| `metrics.py` | Özet kartları ve her başarı kriteri için bir fonksiyon | Yeni metrik veya kart |
| `charts.py` | Harita, zaman grafikleri ve iki tablo | Yeni grafik, tablo sütunu, harita katmanı |
| `app.py` | Sayfa düzeni (hesap yapmaz); Streamlit'i yalnız bu dosya kullanır | Sayfaya bir şey eklenecekse |

### Sayfa açılınca, parametre değişince veya kaydırıcı oynayınca ne olur?

Streamlit her kullanıcı hareketinde `app.py` dosyasını **baştan sona yeniden çalıştırır**:

1. Kenar çubuğu çizilir: dosya listesi (`loader.list_log_files`), uçuş seçimi, parametre kutuları → `Params`.
2. `load_flight_cached` dosyayı okur. Sonuç önbellekte tutulur (anahtar: dosya yolu + değişiklik zamanı), yani
   aynı dosya ikinci kez okunmaz; blackbox logu da yalnızca bir kez çözülür.
3. `events.find_events` ve `metrics.compute_metrics` **yeni parametrelerle yeniden** hesaplanır (R değişince
   FENCE_BREACH zamanı da değişir).
4. Zaman kaydırıcısı `cursor_s` değerini verir. Bu değer `charts.map_figure` fonksiyonuna (haritadaki yeşil nokta,
   `loader.nearest_row` ile en yakın satırda) ve her zaman grafiğine (dikey çizgi) gider.
5. Harita, grafikler ve tablolar yeniden çizilir. ~6.000 satırlık bir uçuşta bu bir saniyeden kısa sürer.

### Parametre mi, limit mi?

- **Parametreler** (`config.DEFAULT_PARAMS`, kenar çubuğu): o uçuşta drona yüklü olan değerler (R, H, m, C …).
  Uçuştan uçuşa değişebilir; "R 40 m olsaydı?" sorusu buradan denenir.
- **Limitler** (`config.py` içinde `SC2_…` … `SC8_…`): projenin RAD'de sabitlenmiş başarı ölçütleri.

## 2. Terimler

| Terim | Anlamı |
|---|---|
| **R** – çit yarıçapı | Dron evden R'den uzakta, onay süresi boyunca kalırsa çit RTH başlatır. |
| **H** – çit yüksekliği | Onay süresi boyunca H'den yüksekte kalmak "irtifa ihlali" olarak raporlanır. |
| **m** – serbest bırakma payı | Çit RTH'si, dron **R − m** çemberinin içine girince kontrolü pilota (EASY) geri verir. |
| **R − m**, **H − m** | Serbest bırakma yarıçapı (harita ve uzaklık grafiği) ve H'nin aynı pay kadar altı (irtifa grafiği). |
| Onay süresi | Bir ihlalin sayılması için R dışında (veya H üstünde) geçmesi gereken süre. |
| **C** – batarya kapasitesi | mAh cinsinden. |
| **r** – iniş rezervi | C'nin hiç uçuşa planlanmayan kısmı (0.20 = %20). |
| **L** – iniş payı | Alçalma ve iniş için gereken şarj (mAh). |
| **k** – dönüş maliyeti | Eve dönüşte metre başına harcanan şarj (mAh/m). Sayfa RTH'li uçuşlarda k'yı ölçer de. |
| **T(d)** | Batarya RTH eşiği: T(d) = C·(1 − r) − L − k·d. Eve d metre uzaktayken harcanan şarj T(d)'ye ulaşınca dron dönmelidir. |
| Uyarı süresi | Batarya uyarısı batarya RTH'sinden bu kadar önce başlar. |
| Ev / iniş noktası | Kalkış noktası (logdaki GPS home, yoksa ilk GPS fix'i) / motorların açık olduğu son nokta. |
| Modlar | **EASY** GPS destekli konum tutma, **NORMAL** kendini dengeleyen mod, **SPORT** acro, **RTH** eve dönüş, **LAND** iniş. |
| PASS / FAIL | Uçuş kriteri test etti; limit sağlandı / sağlanmadı. |
| N/A | Bu uçuş kriteri test etmedi (ör. 60 s hover yok, batarya RTH'si yok). |
| INFO | Limiti olmayan bilgi satırı (ör. bağlantının geri geldiği an). |

Kriterler: **SC-2** hover sapması, **SC-3** RTH iniş hatası, **SC-4** failsafe tepki süresi, **SC-5** batarya RTH
eşiği ve kalan şarj, **SC-6** çit tepki süresi ve taşma, **SC-8** 10 dakikalık destekli uçuş. Tanımlar:
`CLAUDE.md` bölüm 10–11, kısa tablo: `README.md`.

## 3. Alıştırmalar

| # | İstek | Dosya(lar) | Satır |
|---|---|---|---|
| 1 | Başarı limitini değiştir | config.py | 1 |
| 2 | Varsayılan parametreyi değiştir | config.py | 1 |
| 3 | Grafik ekle | charts.py, app.py | 4 |
| 4 | Yer hızını km/h göster | charts.py, config.py | 3 |
| 5 | Özet kartı ekle | metrics.py | 1 |
| 6 | Olay ekle (LOW_SATS) | events.py, config.py | 3 |
| 7 | Limitli metrik ekle | metrics.py, config.py | 6 |
| 8 | Mod rengini değiştir | config.py | 1 |
| 9 | Serbest bırakma çemberini gizle/göster | charts.py, config.py | 5 |
| 10 | Kriter tablosunu CSV indir | app.py | 1 |
| 11 | Uçuşun bir zaman aralığını analiz et | app.py | 3 |
| 12 | Hover kuralını değiştir | config.py | 1 |
| 13 | Olay tablosuna sütun ekle | charts.py, app.py | 4 |
| 14 | Etiketleri değiştir / çevir | charts.py (veya app.py, metrics.py) | 2 |
| 15 | Düşük voltaj uyarısı | app.py, config.py | 3 |

(Satır sayısına fonksiyonlar arasındaki boş satırlar dahil değildir.)

---

### Alıştırma 1 – Başarı limitini değiştir (SC-2 RMS 1.5 → 1.0 m)

**Dosya:** `config.py`, "success-criteria LIMITS" bölümü.

```diff
-SC2_RMS_MAX_M = 1.5                          # hover drift RMS [m]
+SC2_RMS_MAX_M = 1.0                          # hover drift RMS [m]
```

**Sayfada:** `samples/hover_after_tuning.csv` → kriter tablosunda "Hover drift RMS | 1.20 m | ≤ 1 m | **FAIL**".

**Not:** `pytest` artık `test_hover_before_tuning_fails_and_after_tuning_passes` testinde hata verir. Bu beklenen
bir durumdur: test, eski limitle "after tuning geçer" sonucunu kontrol ediyor. Testlerin bir sonuç değişikliğini
yakaladığını göstermek için iyi bir örnektir. Sonra geri alın.

### Alıştırma 2 – Varsayılan parametreyi değiştir (R 50 → 40 m)

**Dosya:** `config.py`, `DEFAULT_PARAMS`.

```diff
 DEFAULT_PARAMS = Params(
-    fence_radius_m=50.0,                     # R: fence radius around home [m]
+    fence_radius_m=40.0,                     # R: fence radius around home [m]
```

**Sayfada:** kenar çubuğunda "R – fence radius" 40.00. `guest_fence.csv`: kırmızı çember küçülür, olay tablosunda
FENCE_BREACH 18.8 s yerine **16.3 s**. Kutu eski değeri gösterirse F5.

**Not:** Testler örneklerin kendi parametreleriyle çalışır; bu değişiklik testleri bozmaz.

### Alıştırma 3 – Grafik ekle (uydu sayısı)

**Dosya 1:** `charts.py`, `speed_chart` fonksiyonunun altına yeni fonksiyon:

```python
def satellites_chart(df: pd.DataFrame, cursor_s: float) -> go.Figure:
    """Number of GPS satellites."""
    return time_chart(df, "gps_sats", "GPS satellites", "count", cursor_s, [])
```

**Dosya 2:** `app.py`, `figures` listesi:

```diff
     charts.mah_chart(df, params, cursor_s),
+    charts.satellites_chart(df, cursor_s),
 ]
```

**Sayfada:** grafiklerin sonunda "GPS satellites" (örneklerde 14'te düz çizgi). `time_chart` her şeyi yapar:
sütun adı, başlık, birim, imleç ve (boş) referans çizgisi listesi verilir.

### Alıştırma 4 – Yer hızını km/h göster

**Dosya 1:** `config.py` (en alta):

```python
KMH_PER_MS = 3.6                             # 1 m/s = 3.6 km/h
```

**Dosya 2:** `charts.py`, `speed_chart`:

```diff
 def speed_chart(df: pd.DataFrame, cursor_s: float) -> go.Figure:
     """GNSS ground speed."""
-    return time_chart(df, "ground_speed_ms", "Ground speed", "m/s", cursor_s, [])
+    df = df.assign(ground_speed_kmh=df["ground_speed_ms"] * config.KMH_PER_MS)   # a copy with a km/h column
+    return time_chart(df, "ground_speed_kmh", "Ground speed", "km/h", cursor_s, [])
```

`df.assign(...)` yeni sütunlu bir **kopya** döndürür; diğer grafikler ve hesaplar etkilenmez.

**Sayfada:** "Ground speed" grafiğinin ekseni km/h; `guest_fence.csv`'de tepe 14.4 km/h (= 4 m/s).

### Alıştırma 5 – Özet kartı ekle (en yüksek yer hızı)

**Dosya:** `metrics.py`, `summary()` içindeki liste:

```diff
         Metric("", "Min voltage", round(df["vbat_v"].min(), 1), "V", "", None),
+        Metric("", "Max speed", round(df["ground_speed_ms"].max(), 1), "m/s", "", None),
         Metric("", "Min satellites", round(df["gps_sats"].min()), "sats", "", None),
```

**Sayfada:** üstte 8. kart "Max speed [m/s] 4.0" (`guest_fence.csv`). `app.py` listedeki her satır için bir kart
çizer; ona dokunmak gerekmez.

### Alıştırma 6 – Olay ekle (uydu sayısı 8'in altına düşünce LOW_SATS)

**Dosya 1:** `config.py` (en alta):

```python
LOW_SATS_LIMIT = 8                           # LOW_SATS event below this many satellites
```

**Dosya 2:** `events.py`, `find_events`:

```diff
 def find_events(df: pd.DataFrame, params: Params) -> list[Event]:
     """All events of the flight, sorted by time."""
+    df = df.assign(low_sats=(df["gps_sats"] < config.LOW_SATS_LIMIT).astype(int))   # 1 = too few satellites
     rows = df.to_dict("records")                 # one dictionary per row, e.g. rows[0]["time_s"]
 ...
     found += limit_breaches(rows, "alt_m", params.fence_height_m, params.confirm_s, "ALTITUDE_BREACH")
+    found += transitions(rows, "low_sats", 0, 1, "LOW_SATS")
     found += fence_releases(found)
```

Açıklama: önce 0/1 bir sütun eklenir (1 = uydu az). Sonra DISARM ve LINK_LOST'u bulan aynı genel dedektör
`transitions`, bu sütunun 0'dan 1'e geçtiği satırları bulur. Olay haritada ve tabloda kendiliğinden görünür.

**Sayfada:** örnek uçuşlarda uydu sayısı hep 14, o yüzden olay çıkmaz. Denemek için `LOW_SATS_LIMIT = 12` yapın ve
kenar çubuğundan `tests/fixtures/decoder_flight.csv` dosyasını yükleyin (uydu 12 → 11 → 10). Olaylar tablosunda
**0.2 s LOW_SATS** görünür. Sonra `logs/decoder_flight.csv` dosyasını silin.

### Alıştırma 7 – Limitli metrik ekle (en yüksek tırmanma hızı ≤ 3 m/s)

**Dosya 1:** `config.py` (en alta):

```python
MAX_CLIMB_RATE_MS = 3.0                      # highest allowed climb rate [m/s]
```

**Dosya 2:** `metrics.py`, dosyanın sonuna yeni fonksiyon ve `compute_metrics` içine bir satır:

```python
def climb_rate(df: pd.DataFrame) -> list[Metric]:
    """Highest climb rate between two rows."""
    rate_ms = df["alt_m"].diff() / df["time_s"].diff()
    return [at_most("Extra", "Max climb rate", rate_ms.max(), "m/s", config.MAX_CLIMB_RATE_MS)]
```

```diff
     rows += endurance(df, params)
+    rows += climb_rate(df)
     return rows
```

`diff()` her satırın bir öncekinden farkıdır: irtifa farkı / zaman farkı = tırmanma hızı. `at_most` limit
karşılaştırmasını, "≤ 3" yazısını ve PASS/FAIL sonucunu üretir.

**Sayfada:** kriter tablosunun sonunda "Extra | Max climb rate | 2.00 m/s | ≤ 3 m/s | **PASS**"
(`guest_fence.csv`). Limiti 1.5 yaparsanız FAIL.

### Alıştırma 8 – Bir uçuş modunun rengini değiştir

**Dosya:** `config.py`, `MODE_COLORS`:

```diff
-    "EASY": "green",
+    "EASY": "cyan",
```

**Sayfada:** haritada EASY noktaları camgöbeği. Herhangi bir CSS renk adı (`"orange"`, `"teal"` …) veya `"#ff8800"`
gibi bir kod kullanılabilir.

### Alıştırma 9 – Serbest bırakma çemberini gizle / göster

**Dosya 1:** `config.py` (en alta):

```python
SHOW_RELEASE_CIRCLE = False                  # draw the release circle R − m on the map
```

**Dosya 2:** `charts.py`, `map_figure`:

```diff
-    release_m = params.fence_radius_m - params.release_margin_m
-    release_lats, release_lons = geo.circle_latlon(home_lat, home_lon, release_m)
-    add_points(figure, release_lats, release_lons, "release R − m", config.RELEASE_COLOR, config.MAP_POINT_SIZE)
+    if config.SHOW_RELEASE_CIRCLE:
+        release_m = params.fence_radius_m - params.release_margin_m
+        release_lats, release_lons = geo.circle_latlon(home_lat, home_lon, release_m)
+        add_points(figure, release_lats, release_lons, "release R − m", config.RELEASE_COLOR, config.MAP_POINT_SIZE)
```

**Sayfada:** turuncu noktalı çember ve lejanttaki "release R − m" kaybolur; `True` yapınca geri gelir.
(Kod değiştirmeden geçici olarak gizlemek için lejantta "release R − m" yazısına tıklamak da yeter.)

### Alıştırma 10 – Kriter tablosunu CSV olarak indir

**Dosya:** `app.py`, kriter tablosunun hemen altı:

```diff
 table_column.dataframe(criteria.style.map(charts.result_style, subset=["Result"]), hide_index=True,
                        height="content")
+table_column.download_button("Download criteria (CSV)", criteria.to_csv(index=False), file_name="criteria.csv")
```

**Sayfada:** tablonun altında "Download criteria (CSV)" düğmesi; tıklayınca `criteria.csv` iner.

### Alıştırma 11 – Uçuşun yalnızca bir zaman aralığını analiz et

**Dosya:** `app.py`, dosya yüklendikten hemen sonra (`end_s` satırının altı):

```diff
 start_s = float(df["time_s"].iloc[0])
 end_s = float(df["time_s"].iloc[-1])
+start_s, end_s = st.sidebar.slider("Analysed time range [s]", start_s, end_s, (start_s, end_s),
+                                   step=config.CURSOR_STEP_S)
+df = df[(df["time_s"] >= start_s) & (df["time_s"] <= end_s)]
 flight_events = events.find_events(df, params)
```

Bir demet `(başlangıç, bitiş)` verildiği için kaydırıcının iki tutamacı olur. Alttaki her şey (olaylar, metrikler,
kartlar, harita, grafikler, zaman imleci) kesilmiş `df` ile çalışır. Ev konumu değişmez, çünkü loader onu her
satıra `home_lat`/`home_lon` olarak yazar.

**Sayfada:** `guest_fence.csv`, aralık 10–30 s → "Flight time 0.3 min", harita yalnız o kısmı gösterir, zaman
imleci 10–30 arasında oynar. Aralığı tek bir ana daraltmayın (başlangıç = bitiş olursa imleç kaydırıcısı hata verir).

### Alıştırma 12 – Hover kuralını değiştir

**Dosya:** `config.py`, "analysis rules":

```diff
-HOVER_MIN_SEGMENT_S = 20                     # shortest hover segment (EASY, sticks centred, armed) [s]
+HOVER_MIN_SEGMENT_S = 30                     # shortest hover segment (EASY, sticks centred, armed) [s]
```

**Sayfada:** örneklerdeki hover 61 s sürdüğü için sonuç değişmez. Etkiyi görmek için 70 yapın →
`hover_after_tuning.csv`'de SC-2 satırları **N/A** (artık hover sayılan bölüm yok; `pytest` hover testlerinde hata
verir, beklenen). Daha geniş stick bandı için `STICK_DEADBAND_US = 30 → 50`. Bu yalnız gerçek loglarda etkilidir;
örnek CSV'lerde `sticks_centered` sütunu hazır gelir.

### Alıştırma 13 – Olay tablosuna sütun ekle (olay anında evden uzaklık)

**Dosya 1:** `charts.py`, `events_table`:

```diff
-def events_table(events: list[Event]) -> pd.DataFrame:
+def events_table(events: list[Event], df: pd.DataFrame) -> pd.DataFrame:
     """The events as a table: time [s] with one decimal, event, detail."""
     table_rows = []
     for event in events:
-        table_rows.append({"Time [s]": round(event.time_s, 1), "Event": event.kind, "Detail": event.detail})
+        dist_m = loader.nearest_row(df, event.time_s)["dist_m"]           # distance from home at the event
+        table_rows.append({"Time [s]": round(event.time_s, 1), "Event": event.kind, "Detail": event.detail,
+                           "Distance [m]": round(dist_m, 1)})
     return pd.DataFrame(table_rows)
```

**Dosya 2:** `app.py`:

```diff
-st.dataframe(charts.events_table(flight_events), hide_index=True, height="content")
+st.dataframe(charts.events_table(flight_events, df), hide_index=True, height="content")
```

`loader.nearest_row(df, zaman)` o zamana en yakın satırı verir (harita imleci de bunu kullanır).

**Sayfada:** `guest_fence.csv` olay tablosunda yeni "Distance [m]" sütunu: FENCE_BREACH 54.1 m, RTH_START 57.3 m.

### Alıştırma 14 – Etiketleri değiştir / çevir

**Dosya:** `charts.py`, grafik fonksiyonları:

```diff
-    return time_chart(df, "alt_m", "Altitude", "m", cursor_s, lines)
+    return time_chart(df, "alt_m", "İrtifa", "m", cursor_s, lines)
```

```diff
-    return time_chart(df, "dist_m", "Distance to home", "m", cursor_s, lines)
+    return time_chart(df, "dist_m", "Eve uzaklık", "m", cursor_s, lines)
```

**Sayfada:** grafik başlıkları Türkçe olur. Diğer etiketlerin yeri:
- kenar çubuğu yazıları ve bölüm başlıkları: `app.py`
- kart adları: `metrics.summary`
- eksen yazısı "time [s]": `charts.time_chart`
- tablo sütun adları: `charts.criteria_table` / `charts.events_table`

**Dikkat:**
- Olay türü adlarını (`"RTH_START"` …) değiştirmeyin. `metrics.py` olayları bu adlarla arıyor.
- Metrik adlarını değiştirirseniz `tests/test_metrics.py` de aynı adı aramalı.

### Alıştırma 15 – Voltaj bir sınırın altına düşerse uyarı göster

**Dosya 1:** `config.py` (en alta):

```python
LOW_VOLTAGE_V = 21.0                         # warning banner below this battery voltage [V]
```

**Dosya 2:** `app.py`, başlığın hemen altı:

```diff
 st.title(f"ATMACA Flight Analyzer – {path.name} · flight {flight_number}")
+if df["vbat_v"].min() < config.LOW_VOLTAGE_V:
+    st.warning(f"Battery voltage fell below {config.LOW_VOLTAGE_V:g} V (minimum {df['vbat_v'].min():.1f} V).")
```

**Sayfada:** `battery_rth.csv` → sarı uyarı "Battery voltage fell below 21 V (minimum 20.2 V)."; `guest_fence.csv`
→ uyarı yok.

## 4. Sık sorulabilecek sorular

- **"Bu sayı nereden geliyor?"** → `config.py`. Programdaki her eşik, renk ve boyut orada, yanında açıklamasıyla.
- **"Olay zamanı neden truth dosyasından 0.1 s farklı?"** Dedektör değişikliğin *ilk* satırını bulur, sentetik
  üretici ise değişiklikten önceki *son* satırı yazar. Testlerde tolerans 0.15 s.
- **"RTH nedeni nereden biliniyor?"** Örneklerde CSV'de yazıyor. Gerçek INAV logunda yok; sırayla FAILSAFE →
  BATTERY → FENCE → PILOT diye tahmin edilir ve "(inferred)" eklenir (`events.infer_rth_reason`).
- **"Gerçek log neden yüklenmiyor?"** Sayfanın altındaki **Data** bölümü hangi sütunun bulunamadığını gösterir; adı
  `config.COLUMN_MAP` içinde düzeltin. Decoder yoksa sayfa nereden indirileceğini yazar.
