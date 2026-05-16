# Feeder Timer

Tempos feeder versenyhorgászathoz készült mobilos segédeszköz.

Az app célja, hogy egyetlen telefonos felületen kiváltsa a külön halszámláló klikkert és a dobástempó figyelésére használt stoppert. Verseny vagy intenzív feeder peca közben gyorsan kezelhető: nagy gombokkal, erős kontraszttal, minimális szöveggel és véletlen nyomások ellen lockolható beállításokkal.

Elsősorban olyan helyzetekre készült, ahol fontos a pontos dobásritmus, a fogások gyors számolása és az adott etap / session idejének követése.

## Élő verzió

GitHub Pages:

```text
https://tonetttoman.github.io/fishing/
```

Telefonon érdemes Chrome-ból megnyitni, majd kezdőképernyőre telepíteni.

## Mire való?

A Feeder Timer három dolgot fog össze egy képernyőre:

- dobástempó figyelése visszaszámlálóval,
- fogások számolása halszámlálóként,
- teljes horgász session / etap idejének mérése.

Így nem kell külön klikkert, külön stoppert és külön órát használni. A cél az, hogy versenytempóban is egyértelmű legyen, mikor kell újradobni, mennyi halnál jársz, és mennyi ideje tart az adott etap.

## Tesztelés és visszajelzés

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

## Fő funkciók

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

## Telefonos telepítés

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

## Használati logika

### Dobás timer

A felső nagy időzítő panel maga a dobás timer gombja.

- érintésre elindul,
- újabb érintésre újraindul a beállított időről,
- minden indítás / újraindítás növeli a dobásszámlálót,
- lejáratkor hangjelzést ad és pirosra vált.

### Hal számláló

A középső nagy panel a halszámláló klikker.

- érintésre `+1` hal,
- unlock módban a bal alsó `-` gombbal javítható.

### Session timer

A felső sor közepén látható session timer az adott horgász etap teljes idejét méri.

- locked módban csak kijelzőként működik,
- unlock módban indítható és megállítható,
- unlock módban a piros `×` gombbal nullázható.

### Lock / unlock

Az alsó panelen lévő lakat védi a véletlen módosításokat.

Locked módban:

- az időállító slider nem módosítható,
- hibajavító gombok nem látszanak,
- session timer csak kijelzőként működik.

Unlocked módban:

- állítható a dobásidő,
- elérhetők a javító gombok,
- indítható / megállítható / nullázható a session timer.

## Fejlesztői futtatás

```bash
npm install
npm run dev
```

Hálózati, telefonos helyi teszthez:

```bash
npm run dev -- --host 0.0.0.0
```

A telefonon a PC helyi IP-címét kell megnyitni, például:

```text
http://192.168.0.226:5173/
```

## Build

```bash
npm run build
npm run preview
```

## Deploy

A projekt GitHub Pages-re deployolódik GitHub Actions segítségével.

Workflow:

```text
.github/workflows/deploy.yml
```

A deploy a `main` branchre kerülő változás után fut.

Publikus URL:

```text
https://tonetttoman.github.io/fishing/
```

## Technológia

- Vite
- React
- TypeScript
- CSS
- GitHub Pages
- GitHub Actions
- PWA manifest
- Service worker

## Aktuális állapot

`v1.0` funkcionális próba előtt / alatt.

A jelenlegi fókusz: vízparti használhatóság, telefonos működés, kezelhetőség erős fényben, vizes kézzel és versenytempóban.
