# Muutospyyntö – Infrastruktuuri (Class 3)

## Perustiedot

**Muutoksen nimi:** Production Network Segmentation and Firewall Policy Update  
**Pyytäjä:** Jonne Silvennoinen  
**Päivämäärä:** 2026-03-15  
**Riskiluokka:** 3  
**Kohdeympäristö:** Production  
**Ehdotettu toteutusaika:** 2026-03-18  

---

## Kuvaus

Tuotantoympäristön verkkoarkkitehtuuria päivitetään lisäämällä backend-palveluille oma verkko-segmentti sekä tarkentamalla palomuurisääntöjä.  
Muutoksen tavoitteena on parantaa tietoturvaa ja rajata palveluiden välistä liikennettä least-privilege -periaatteen mukaisesti.

---

**Riskiperustelu:**

Muutos kohdistuu tuotantoverkon liikenteenohjaukseen ja palomuurisääntöihin. Virheellinen konfiguraatio voi estää kriittisten palveluiden välisen liikenteen ja aiheuttaa palvelukatkon.  
Koska muutos vaikuttaa infrastruktuurin turvallisuusrakenteeseen ja tuotantoympäristön saatavuuteen, se luokitellaan Riskiluokka 3 mukaiseksi korkeaksi riskiksi.

---

## Vaikutusanalyysi

- Mahdollinen hetkellinen palvelukatkos virhetilanteessa  
- Vaikutus backend-palveluiden väliseen liikenteeseen  
- Ei muutoksia sovelluskoodiin tai asiakasdataan  

---

## Testaussuunnitelma

- Verkko- ja palomuurikonfiguraation testaus staging-ympäristössä  
- Simuloitu palveluliikenne segmenttien välillä  
- Monitorointi (logit ja health-checkit) ennen ja jälkeen muutoksen  

---

## Palautussuunnitelma

- Välitön rollback aiempaan palomuurikonfiguraatioon  
- Konfiguraation varmuuskopio ennen muutosta  
- Muutoksen peruutus Infrastructure-as-Code -repositoryn kautta  

**Onko palautus testattu?** Kyllä  

---

## Hyväksyntäketju

**Hyväksyjä 1:** DevOps Lead  
**Hyväksyjä 2:** CISO  
**Hyväksyjä 3:** CTO
