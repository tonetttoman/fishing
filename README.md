# Feeder Timer

Egyszerű, mobilra optimalizált feeder horgász segédapp dobásidőzítéshez, fogásszámláláshoz és session idő méréséhez.

Az app elsődleges célja, hogy vízparton, telefonról, nagy gombokkal és erős kontraszttal gyorsan kezelhető legyen.

## Élő verzió

GitHub Pages:

```text
https://tonetttoman.github.io/fishing/
```

Telefonon érdemes Chrome-ból megnyitni, majd kezdőképernyőre telepíteni.

## Fő funkciók

- állítható dobás-visszaszámláló `5 mp` és `60 perc` között,
- alapértelmezett idő: `02:30`,
- a nagy időzítő panel érintésre indítja vagy újraindítja a dobásidőt,
- lejáratkor hangjelzés,
- lejáratkor a timer panel pirosra vált,
- külön dobásszámláló,
- külön halszámláló,
- hibajavító `-` gombok unlock módban,
- dobásszámláló nullázása unlock módban,
- külön session timer,
- session start/stop csak unlock módban,
- session reset csak unlock módban,
- dátum és pontos idő kijelzés,
- beállítási slider lockolható,
- PWA metadata, ikon és service worker,
- kezdőképernyőről app-szerűen indítható.

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

A középső nagy panel a halszámláló.

- érintésre `+1` hal,
- unlock módban a bal alsó `-` gombbal javítható.

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

A jelenlegi fókusz: vízparti használhatóság, telefonos működés, kezelhetőség erős fényben és vizes kézzel.
