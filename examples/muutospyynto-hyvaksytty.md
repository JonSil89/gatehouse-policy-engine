# 🏛️ Muutospyyntö: Tietokantaklusterin tietoturvapäivitys

## Perustiedot
**Muutoksen nimi:** Kriittinen tietoturvapäivitys (v2.4.1)
**Pyytäjä:** Jonne Järjestelmäylläpitäjä
**Päivämäärä:** 2026-04-21
**Riskiluokka:** 2
**Kohdeympäristö:** staging

### Riskiluokan perustelu
Muutos koskee staging-ympäristön tietokantaa. Vaikka kyseessä on vain päivitys, se vaatii palvelun uudelleenkäynnistyksen, minkä vuoksi luokka on asetettu keskitasolle (2).

---

## Kuvaus
Tämä muutos päivittää PostgreSQL-klusterin uusimpaan tietoturvaversioon. Päivitys korjaa havaitun haavoittuvuuden ja parantaa suorituskykyä.

**Suoritussuunnitelma:**
1. Otetaan täysi snapshot tietokannasta.
2. Ajetaan päivitysskripti CI/CD-putken kautta.
3. Varmistetaan versioarvo päivityksen jälkeen.

---

## Vaikutusanalyysi
**Vaikutus palveluun:** Arvioitu käyttökatko on noin 30 sekuntia uudelleenkäynnistyksen aikana.
**Kriittiset komponentit:** Staging-tietokanta ja siihen liittyvät API-palvelut.
**Tehtävien eriyttäminen:** Toteuttaja ja hyväksyjä ovat eri henkilöitä ISO 27001 -vaatimusten mukaisesti.

---

## Testaussuunnitelma
**Testausympäristö:** staging
**Testitapaukset:**
- [x] Tietokantayhteys toimii päivityksen jälkeen.
- [x] Datan lukeminen ja kirjoittaminen onnistuu.
- [x] Sovelluslokit eivät näytä virheitä.

---

## Palautussuunnitelma
**Palautusstrategia:** snapshot restore
**Onko palautus testattu?** Kyllä
**Palautusohjeet:** Jos päivitys epäonnistuu, palautetaan järjestelmä kohdan 1 snapshotista AWS-konsolin kautta.

---

## Hyväksynnät
**Hyväksyjä 1:** @TiinaTiimivastaava
**Hyväksyjä 2:** @MattiMuutoshallinta