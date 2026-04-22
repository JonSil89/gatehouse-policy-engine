# Palautussuunnitelma (Rollback Plan)

## Perustiedot

- **Liittyy muutospyyntöön:** CI/CD-pipelinen siirto GitHub Actions v4:ään
- **Riskiluokka:** 2
- **Palautuksen vastuuhenkilö:** Matti Meikäläinen
- **Laadittu:** 2026-02-24

## Palautusstrategia

### Ensisijainen palautustapa
- **Menetelmä:** git revert
- **Kuvaus:** Palautetaan workflow-tiedostot edelliseen versioon git revert -komennolla. Tämä luo uuden commitin, joka kumoaa muutokset, säilyttäen historian.
- **Arvioitu kesto:** 10 minuuttia

### Vaihtoehtoinen palautustapa (jos ensisijainen epäonnistuu)
- **Menetelmä:** Manuaalinen tiedostojen palautus
- **Kuvaus:** Kopioidaan vanhat workflow-tiedostot varmuuskopiosta ja pushataan suoraan mainiin emergency-prosessin kautta.
- **Arvioitu kesto:** 20 minuuttia

## Palautuksen vaiheet

1. **Vaihe 1:** Tunnista palautettava commit
   - Komento/toimenpide: `git log --oneline -5`
   - Odotettu tulos: Nähdään viimeisimmät commitit ja tunnistetaan palautettava hash

2. **Vaihe 2:** Suorita palautus
   - Komento/toimenpide: `git revert <commit-hash> --no-edit`
   - Odotettu tulos: Uusi commit luodaan, joka kumoaa muutokset

3. **Vaihe 3:** Pushaa palautus ja varmista
   - Komento/toimenpide: `git push origin main`
   - Odotettu tulos: CI/CD-pipeline käynnistyy vanhoilla Actions-versioilla

4. **Vaihe 4:** Varmista palvelun toimivuus
   - Komento/toimenpide: Tarkista GitHub Actions -välilehdeltä, että pipeline suoriutuu onnistuneesti
   - Odotettu tulos: Vihreä tila kaikissa workflow-ajoissa

## Palautuksen laukaisukriteerit (Rollback Triggers)

Palautus käynnistetään, jos jokin seuraavista toteutuu:

- [x] Palvelu ei vastaa 15 minuutin kuluessa muutoksesta
- [x] Virheaste nousee yli 20% normaalista
- [x] Kriittinen toiminnallisuus on rikki
- [x] Tietoturvahavainto (välitön palautus)
- [x] Muu: Pipeline-ajot epäonnistuvat toistuvasti (3+ peräkkäistä virhettä)

## Datan käsittely

- **Sisältääkö muutos dataan kohdistuvia muutoksia?** Ei
- **Onko data varmuuskopioitu ennen muutosta?** Ei sovellettavissa
- **Varmuuskopion sijainti:** Ei sovellettavissa
- **Datahäviön riski palautuksessa:** Ei

## Testaus

- **Onko palautus testattu staging-ympäristössä?** Kyllä
- **Testauspäivämäärä:** 2026-02-20
- **Testaustulokset:** Git revert suoritettiin onnistuneesti staging-ympäristössä. Pipeline palautui toimintakuntoon 8 minuutissa. Ei havaittu sivuvaikutuksia.

## Kommunikaatio palautustilanteessa

- **Kuka ilmoittaa sidosryhmille?** Matti Meikäläinen
- **Ilmoituskanavat:** Slack (#infra-alerts), sähköposti (dev-team@company.fi)
- **Viestirunko:** "CI/CD-pipeline palautettu edelliseen versioon. Syy: [kuvaus]. Pipeline toimii normaalisti. Uusi muutosyritys suunnitteilla aikaisintaan [pvm]."

## Palautuksen jälkeiset toimenpiteet

1. Varmista palvelun toimivuus monitoroinnilla (30 min)
2. Kirjaa incident/postmortem
3. Päivitä muutospyyntö palautuksen syillä
4. Suunnittele korjattu muutos root cause -analyysin perusteella

## Tarkistuslista

- [x] Palautusstrategia määritelty
- [x] Vaiheet dokumentoitu riittävällä tarkkuudella
- [x] Laukaisukriteerit määritelty
- [x] Datan varmuuskopiointi varmistettu
- [x] Palautus testattu (luokka 3)
- [ ] Kommunikaatiosuunnitelma laadittu (luokka 3)
