# Feeder Timer

**English:** Mobile feeder fishing timer for competition anglers. It combines a cast rhythm timer, fish counter and session timer in one phone-friendly PWA.

**Magyar:** Mobilos feeder versenyhorgász segédeszköz dobástempóhoz, halszámláláshoz és session / etap időméréshez.

## Language / Nyelv

- [English description](#english)
- [Magyar leírás](#magyar)
- [Development / Fejlesztés](#development--fejlesztés)

## English

Feeder Timer is a mobile-first helper app for competitive feeder and method feeder anglers.

It is designed to replace two common tools used during fast-paced fishing: a separate fish counter clicker and a stopwatch used to monitor cast rhythm. The goal is to keep the most important timing and counting information on one simple, high-contrast phone screen.

The app is especially useful when cast rhythm matters, fish need to be counted quickly, and the total session or match section time should stay visible.

### Live app

GitHub Pages:

```text
https://tonetttoman.github.io/fishing/
```

On mobile, open it in Chrome and install it to the home screen.

### What is it for?

Feeder Timer combines three competition-focused tools:

- cast rhythm countdown timer,
- fish counter clicker,
- session / section timer.

This means you do not need a separate clicker, stopwatch and clock. During competition pace, the app helps you see when to recast, how many fish you have counted, and how long the current session or section has been running.

### Testing and feedback

The project is currently in `v1.0` testing state. Feedback is especially useful from feeder competition anglers, method feeder anglers and anyone who actively tracks cast rhythm and fish count while fishing.

App:

```text
https://tonetttoman.github.io/fishing/
```

Repository:

```text
https://github.com/tonetttoman/fishing
```

Bug reports and feature ideas are best submitted as GitHub Issues:

```text
https://github.com/tonetttoman/fishing/issues
```

Useful testing feedback includes:

- visibility in strong sunlight,
- usability with wet hands,
- anything annoying during fast fishing pace,
- whether the main buttons are in the right place,
- whether fish and cast counting is fast enough,
- whether the session timer placement is useful,
- anything missing for practical use on the bank.

For bug reports, please include:

- phone model,
- browser,
- whether the app was opened from the home screen or in the browser,
- what you tapped before the issue happened,
- screenshot if possible.

### Main features

- cast rhythm timer from `5 seconds` to `60 minutes`,
- default cast time: `02:30`,
- large top panel starts or restarts the cast timer,
- sound alert and red warning state when the timer expires,
- automatic cast counting on each timer start / restart,
- large fish counter panel usable as a clicker,
- fish count and cast count correction in unlock mode,
- cast counter reset in unlock mode,
- separate session timer for measuring the current session / match section,
- session start/stop only in unlock mode,
- session reset only in unlock mode,
- lockable interface to prevent accidental touches,
- date and current time display,
- mobile-first, outdoor-focused high-contrast UI,
- installable PWA that can be launched from the phone home screen.

### Mobile installation

1. Open on your phone:

```text
https://tonetttoman.github.io/fishing/
```

2. Chrome menu:

```text
Install
```

or:

```text
Add to Home screen
```

3. Start the app from the home screen icon, not from a browser tab.

### Usage logic

#### Cast timer

The large top timer panel is the cast timer button.

- tap to start,
- tap again to restart from the configured time,
- every start / restart increases the cast counter,
- when time expires, the app plays a sound alert and the timer panel turns red.

#### Fish counter

The large middle panel works as the fish counter clicker.

- tap for `+1` fish,
- in unlock mode, use the bottom-left `-` button to correct mistakes.

#### Session timer

The session timer is shown in the middle of the top row and measures the full fishing session or match section.

- in locked mode, it is display-only,
- in unlock mode, it can be started and stopped,
- in unlock mode, the red `×` button resets it.

#### Lock / unlock

The lock button in the bottom panel protects against accidental changes.

Locked mode:

- time slider is disabled,
- correction buttons are hidden,
- session timer is display-only.

Unlocked mode:

- cast time can be adjusted,
- correction buttons are available,
- session timer can be started, stopped and reset.

## Magyar

A Feeder Timer tempós feeder versenyhorgászathoz készült mobilos segédeszköz.

Az app célja, hogy egyetlen telefonos felületen kiváltsa a külön halszámláló klikkert és a dobástempó figyelésére használt stoppert. Verseny vagy intenzív feeder peca közben gyorsan kezelhető: nagy gombokkal, erős kontraszttal, minimális szöveggel és véletlen nyomások ellen lockolható beállításokkal.

Elsősorban olyan helyzetekre készült, ahol fontos a pontos dobásritmus, a fogások gyors számolása és az adott etap / session idejének követése.

### Élő verzió

GitHub Pages:

```text
https://tonetttoman.github.io/fishing/
```

Telefonon érdemes Chrome-ból megnyitni, majd kezdőképernyőre telepíteni.

### Mire való?

A Feeder Timer három dolgot fog össze egy képernyőre:

- dobástempó figyelése visszaszámlálóval,
- fogások számolása halszámlálóként,
- teljes horgász session / etap idejének mérése.

Így nem kell külön klikkert, külön stoppert és külön órát használni. A cél az, hogy versenytempóban is egyértelmű legyen, mikor kell újradobni, mennyi halnál jársz, és mennyi ideje tart az adott etap.

### Tesztelés és visszajelzés

A projekt jelenleg `v1.0` tesztállapotban van. Elsősorban feeder versenyhorgászok, intenzív method / feeder pecát gyakorlók és olyan horgászok visszajelzése hasznos, akik ténylegesen figyelik a dobástempót és számolják a fogásokat.

App:

```text
https://tonetttoman.github.io/fishing/
```

Repository:

```text
https://github.com/tonetttoman/fishing
```

Hibajelentést és fejlesztési ötletet GitHub Issue-ként érdemes rögzíteni:

```text
https://github.com/tonetttoman/fishing/issues
```

Tesztelésnél különösen hasznos visszajelzés:

- mennyire jól látható erős napfényben,
- mennyire kezelhető vizes kézzel,
- zavaró-e bármi versenytempóban,
- jó helyen vannak-e a fő gombok,
- elég gyors-e a hal és dobás számolása,
- hasznos-e a session timer elhelyezése,
- hiányzik-e valami a valódi vízparti használathoz.

Hibajelentéshez érdemes megadni:

- milyen telefonon tesztelted,
- milyen böngészőben futott,
- kezdőképernyőről vagy böngészőből indítottad-e,
- pontosan mit nyomtál meg, amikor a hiba előjött,
- lehetőleg képernyőképet is.

### Fő funkciók

- dobástempó-időzítő `5 mp` és `60 perc` között,
- alapértelmezett dobásidő: `02:30`,
- a nagy felső panel érintésre indítja vagy újraindítja a dobásidőt,
- lejáratkor hangjelzés és piros figyelmeztető állapot,
- automatikus dobásszámlálás minden újraindításnál,
- nagy halszámláló panel, amely klikkerként használható,
- halszám és dobásszám javítása unlock módban,
- dobásszámláló nullázása unlock módban,
- külön session timer az adott peca / etap teljes idejének mérésére,
- session start/stop csak unlock módban,
- session reset csak unlock módban,
- lockolt kezelőfelület a véletlen nyomások ellen,
- dátum és pontos idő kijelzés,
- mobilra és kültéri használatra optimalizált, nagy kontrasztú felület,
- kezdőképernyőről app-szerűen indítható PWA.

### Telefonos telepítés

1. Nyisd meg telefonon:

```text
https://tonetttoman.github.io/fishing/
```

2. Chrome menü:

```text
Telepítés
```

vagy:

```text
Hozzáadás kezdőképernyőhöz
```

3. Ezután az appot a kezdőképernyős ikonról indítsd, ne böngészőfülből.

### Használati logika

#### Dobás timer

A felső nagy időzítő panel maga a dobás timer gombja.

- érintésre elindul,
- újabb érintésre újraindul a beállított időről,
- minden indítás / újraindítás növeli a dobásszámlálót,
- lejáratkor hangjelzést ad és pirosra vált.

#### Hal számláló

A középső nagy panel a halszámláló klikker.

- érintésre `+1` hal,
- unlock módban a bal alsó `-` gombbal javítható.

#### Session timer

A felső sor közepén látható session timer az adott horgász etap teljes idejét méri.

- locked módban csak kijelzőként működik,
- unlock módban indítható és megállítható,
- unlock módban a piros `×` gombbal nullázható.

#### Lock / unlock

Az alsó panelen lévő lakat védi a véletlen módosításokat.

Locked módban:

- az időállító slider nem módosítható,
- hibajavító gombok nem látszanak,
- session timer csak kijelzőként működik.

Unlocked módban:

- állítható a dobásidő,
- elérhetők a javító gombok,
- indítható / megállítható / nullázható a session timer.

## Development / Fejlesztés

### Development run / Fejlesztői futtatás

```bash
npm install
npm run dev
```

Local network mobile test / Hálózati, telefonos helyi teszt:

```bash
npm run dev -- --host 0.0.0.0
```

Open the local IP address on the phone / Telefonon a PC helyi IP-címét kell megnyitni, például:

```text
http://192.168.0.226:5173/
```

### Build

```bash
npm run build
npm run preview
```

### Deploy

The project is deployed to GitHub Pages with GitHub Actions.

A projekt GitHub Pages-re deployolódik GitHub Actions segítségével.

Workflow:

```text
.github/workflows/deploy.yml
```

Deploy runs after changes are pushed to `main`.

A deploy a `main` branchre kerülő változás után fut.

Public URL / Publikus URL:

```text
https://tonetttoman.github.io/fishing/
```

### Tech stack / Technológia

- Vite
- React
- TypeScript
- CSS
- GitHub Pages
- GitHub Actions
- PWA manifest
- Service worker

## Current status / Aktuális állapot

`v1.0` is currently in practical field testing.

`v1.0` funkcionális, vízparti tesztelés előtt / alatt.

Current focus: practical use on the bank, phone behavior, visibility in strong sunlight, wet-hand handling and competition-pace operation.

Jelenlegi fókusz: vízparti használhatóság, telefonos működés, kezelhetőség erős fényben, vizes kézzel és versenytempóban.
