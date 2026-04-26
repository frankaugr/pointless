"""Curated category definitions for the static revision app.

The old prototype treated Wikidata as the authority for every answer set. That
is convenient, but it is too loose for Pointless-style revision: finite trivia
sets need stable counts, reviewable aliases, and category-specific attributes
for narrowed questions. Wikidata and Wikipedia pageviews are still useful
enrichment sources, but these fixtures are the canonical v1 data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(frozen=True)
class AnswerSpec:
    name: str
    aliases: tuple[str, ...] = ()
    attrs: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
    qid: str | None = None
    wiki: str | None = None
    fame: int = 5
    pageviews: int | None = None


@dataclass(frozen=True)
class CategorySpec:
    slug: str
    name: str
    description: str
    tags: tuple[str, ...]
    answer_kind: str
    expected_count: int
    display_fields: tuple[str, ...]
    question_templates: tuple[dict[str, Any], ...]
    answers: tuple[AnswerSpec, ...]
    sources: tuple[dict[str, str], ...] = ()


def slugify(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def wiki_url(title: str) -> str:
    return "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")


def answer(
    name: str,
    *,
    aliases: tuple[str, ...] | list[str] = (),
    attrs: dict[str, Any] | None = None,
    id: str | None = None,
    qid: str | None = None,
    wiki: str | None = None,
    fame: int = 5,
    pageviews: int | None = None,
) -> AnswerSpec:
    return AnswerSpec(
        id=id,
        name=name,
        aliases=tuple(a for a in aliases if a),
        attrs=attrs or {},
        qid=qid,
        wiki=wiki or wiki_url(name),
        fame=fame,
        pageviews=pageviews,
    )


def _split_aliases(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(";") if part.strip())


def _rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in text.strip().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rows.append([part.strip() for part in line.split("|")])
    return rows


def _century(year: int) -> str:
    return f"{((year - 1) // 100) + 1}th century"


COMMON_NAME_TEMPLATES = (
    {
        "id": "name-starts-consonant",
        "kind": "starts_with_consonant",
        "field": "name",
        "prompt": "{category} whose name begins with a consonant",
    },
    {
        "id": "name-contains-pointless",
        "kind": "contains_any_letters",
        "field": "name",
        "letters": "POINTLESS",
        "prompt": "{category} containing at least one of the letters P, O, I, N, T, L, E or S",
    },
    {
        "id": "short-name",
        "kind": "name_length_at_most",
        "field": "name",
        "max": 6,
        "prompt": "{category} with names of six letters or fewer",
    },
)


ELEMENT_ROWS = """
1|H|Hydrogen|nonmetal|10
2|He|Helium|noble gas|10
3|Li|Lithium|alkali metal|8
4|Be|Beryllium|alkaline earth metal|5
5|B|Boron|metalloid|6
6|C|Carbon|nonmetal|10
7|N|Nitrogen|nonmetal|10
8|O|Oxygen|nonmetal|10
9|F|Fluorine|halogen|8
10|Ne|Neon|noble gas|9
11|Na|Sodium|alkali metal|10
12|Mg|Magnesium|alkaline earth metal|9
13|Al|Aluminium|post-transition metal|10|Aluminum
14|Si|Silicon|metalloid|9
15|P|Phosphorus|nonmetal|8
16|S|Sulfur|nonmetal|9|Sulphur
17|Cl|Chlorine|halogen|9
18|Ar|Argon|noble gas|8
19|K|Potassium|alkali metal|9
20|Ca|Calcium|alkaline earth metal|10
21|Sc|Scandium|transition metal|4
22|Ti|Titanium|transition metal|9
23|V|Vanadium|transition metal|5
24|Cr|Chromium|transition metal|8
25|Mn|Manganese|transition metal|7
26|Fe|Iron|transition metal|10
27|Co|Cobalt|transition metal|8
28|Ni|Nickel|transition metal|9
29|Cu|Copper|transition metal|10
30|Zn|Zinc|transition metal|10
31|Ga|Gallium|post-transition metal|7
32|Ge|Germanium|metalloid|6
33|As|Arsenic|metalloid|8
34|Se|Selenium|nonmetal|7
35|Br|Bromine|halogen|7
36|Kr|Krypton|noble gas|8
37|Rb|Rubidium|alkali metal|5
38|Sr|Strontium|alkaline earth metal|6
39|Y|Yttrium|transition metal|5
40|Zr|Zirconium|transition metal|6
41|Nb|Niobium|transition metal|5
42|Mo|Molybdenum|transition metal|6
43|Tc|Technetium|transition metal|6
44|Ru|Ruthenium|transition metal|5
45|Rh|Rhodium|transition metal|7
46|Pd|Palladium|transition metal|8
47|Ag|Silver|transition metal|10
48|Cd|Cadmium|transition metal|7
49|In|Indium|post-transition metal|5
50|Sn|Tin|post-transition metal|9
51|Sb|Antimony|metalloid|6
52|Te|Tellurium|metalloid|5
53|I|Iodine|halogen|9
54|Xe|Xenon|noble gas|8
55|Cs|Caesium|alkali metal|7|Cesium
56|Ba|Barium|alkaline earth metal|7
57|La|Lanthanum|lanthanide|5
58|Ce|Cerium|lanthanide|5
59|Pr|Praseodymium|lanthanide|3
60|Nd|Neodymium|lanthanide|7
61|Pm|Promethium|lanthanide|4
62|Sm|Samarium|lanthanide|4
63|Eu|Europium|lanthanide|5
64|Gd|Gadolinium|lanthanide|5
65|Tb|Terbium|lanthanide|4
66|Dy|Dysprosium|lanthanide|4
67|Ho|Holmium|lanthanide|3
68|Er|Erbium|lanthanide|4
69|Tm|Thulium|lanthanide|3
70|Yb|Ytterbium|lanthanide|4
71|Lu|Lutetium|lanthanide|4
72|Hf|Hafnium|transition metal|5
73|Ta|Tantalum|transition metal|6
74|W|Tungsten|transition metal|8|Wolfram
75|Re|Rhenium|transition metal|5
76|Os|Osmium|transition metal|6
77|Ir|Iridium|transition metal|7
78|Pt|Platinum|transition metal|10
79|Au|Gold|transition metal|10
80|Hg|Mercury|transition metal|10|Quicksilver
81|Tl|Thallium|post-transition metal|6
82|Pb|Lead|post-transition metal|10
83|Bi|Bismuth|post-transition metal|7
84|Po|Polonium|post-transition metal|7
85|At|Astatine|halogen|5
86|Rn|Radon|noble gas|8
87|Fr|Francium|alkali metal|5
88|Ra|Radium|alkaline earth metal|8
89|Ac|Actinium|actinide|4
90|Th|Thorium|actinide|7
91|Pa|Protactinium|actinide|3
92|U|Uranium|actinide|10
93|Np|Neptunium|actinide|6
94|Pu|Plutonium|actinide|9
95|Am|Americium|actinide|6
96|Cm|Curium|actinide|5
97|Bk|Berkelium|actinide|4
98|Cf|Californium|actinide|6
99|Es|Einsteinium|actinide|6
100|Fm|Fermium|actinide|5
101|Md|Mendelevium|actinide|4
102|No|Nobelium|actinide|5
103|Lr|Lawrencium|actinide|4
104|Rf|Rutherfordium|transition metal|4
105|Db|Dubnium|transition metal|4
106|Sg|Seaborgium|transition metal|4
107|Bh|Bohrium|transition metal|3
108|Hs|Hassium|transition metal|3
109|Mt|Meitnerium|unknown|3
110|Ds|Darmstadtium|unknown|3
111|Rg|Roentgenium|unknown|3
112|Cn|Copernicium|transition metal|4
113|Nh|Nihonium|post-transition metal|4
114|Fl|Flerovium|post-transition metal|4
115|Mc|Moscovium|post-transition metal|4
116|Lv|Livermorium|post-transition metal|4
117|Ts|Tennessine|halogen|5
118|Og|Oganesson|noble gas|5
"""


COUNTRY_ROWS = """
Afghanistan|Kabul|Asia|
Albania|Tirana|Europe|
Algeria|Algiers|Africa|
Andorra|Andorra la Vella|Europe|
Angola|Luanda|Africa|
Antigua and Barbuda|Saint John's|North America|
Argentina|Buenos Aires|South America|
Armenia|Yerevan|Asia|
Australia|Canberra|Oceania|
Austria|Vienna|Europe|
Azerbaijan|Baku|Asia|
Bahamas|Nassau|North America|The Bahamas
Bahrain|Manama|Asia|
Bangladesh|Dhaka|Asia|
Barbados|Bridgetown|North America|
Belarus|Minsk|Europe|
Belgium|Brussels|Europe|
Belize|Belmopan|North America|
Benin|Porto-Novo|Africa|
Bhutan|Thimphu|Asia|
Bolivia|Sucre|South America|
Bosnia and Herzegovina|Sarajevo|Europe|Bosnia
Botswana|Gaborone|Africa|
Brazil|Brasilia|South America|
Brunei|Bandar Seri Begawan|Asia|
Bulgaria|Sofia|Europe|
Burkina Faso|Ouagadougou|Africa|
Burundi|Gitega|Africa|
Cambodia|Phnom Penh|Asia|
Cameroon|Yaounde|Africa|
Canada|Ottawa|North America|
Cape Verde|Praia|Africa|Cabo Verde
Central African Republic|Bangui|Africa|CAR
Chad|N'Djamena|Africa|
Chile|Santiago|South America|
China|Beijing|Asia|
Colombia|Bogota|South America|
Comoros|Moroni|Africa|
Congo, Democratic Republic of the|Kinshasa|Africa|Democratic Republic of the Congo;DR Congo;Congo-Kinshasa
Congo, Republic of the|Brazzaville|Africa|Republic of the Congo;Congo-Brazzaville
Costa Rica|San Jose|North America|
Cote d'Ivoire|Yamoussoukro|Africa|Ivory Coast
Croatia|Zagreb|Europe|
Cuba|Havana|North America|
Cyprus|Nicosia|Europe|
Czechia|Prague|Europe|Czech Republic
Denmark|Copenhagen|Europe|
Djibouti|Djibouti|Africa|
Dominica|Roseau|North America|
Dominican Republic|Santo Domingo|North America|
Ecuador|Quito|South America|
Egypt|Cairo|Africa|
El Salvador|San Salvador|North America|
Equatorial Guinea|Malabo|Africa|
Eritrea|Asmara|Africa|
Estonia|Tallinn|Europe|
Eswatini|Mbabane|Africa|Swaziland
Ethiopia|Addis Ababa|Africa|
Fiji|Suva|Oceania|
Finland|Helsinki|Europe|
France|Paris|Europe|
Gabon|Libreville|Africa|
Gambia|Banjul|Africa|The Gambia
Georgia|Tbilisi|Europe|
Germany|Berlin|Europe|
Ghana|Accra|Africa|
Greece|Athens|Europe|
Grenada|Saint George's|North America|
Guatemala|Guatemala City|North America|
Guinea|Conakry|Africa|
Guinea-Bissau|Bissau|Africa|
Guyana|Georgetown|South America|
Haiti|Port-au-Prince|North America|
Honduras|Tegucigalpa|North America|
Hungary|Budapest|Europe|
Iceland|Reykjavik|Europe|
India|New Delhi|Asia|
Indonesia|Jakarta|Asia|
Iran|Tehran|Asia|
Iraq|Baghdad|Asia|
Ireland|Dublin|Europe|Republic of Ireland
Israel|Jerusalem|Asia|
Italy|Rome|Europe|
Jamaica|Kingston|North America|
Japan|Tokyo|Asia|
Jordan|Amman|Asia|
Kazakhstan|Astana|Asia|
Kenya|Nairobi|Africa|
Kiribati|South Tarawa|Oceania|
Kuwait|Kuwait City|Asia|
Kyrgyzstan|Bishkek|Asia|
Laos|Vientiane|Asia|
Latvia|Riga|Europe|
Lebanon|Beirut|Asia|
Lesotho|Maseru|Africa|
Liberia|Monrovia|Africa|
Libya|Tripoli|Africa|
Liechtenstein|Vaduz|Europe|
Lithuania|Vilnius|Europe|
Luxembourg|Luxembourg|Europe|
Madagascar|Antananarivo|Africa|
Malawi|Lilongwe|Africa|
Malaysia|Kuala Lumpur|Asia|
Maldives|Male|Asia|
Mali|Bamako|Africa|
Malta|Valletta|Europe|
Marshall Islands|Majuro|Oceania|
Mauritania|Nouakchott|Africa|
Mauritius|Port Louis|Africa|
Mexico|Mexico City|North America|
Micronesia|Palikir|Oceania|Federated States of Micronesia
Moldova|Chisinau|Europe|
Monaco|Monaco|Europe|
Mongolia|Ulaanbaatar|Asia|
Montenegro|Podgorica|Europe|
Morocco|Rabat|Africa|
Mozambique|Maputo|Africa|
Myanmar|Naypyidaw|Asia|Burma
Namibia|Windhoek|Africa|
Nauru|Yaren|Oceania|
Nepal|Kathmandu|Asia|
Netherlands|Amsterdam|Europe|Holland
New Zealand|Wellington|Oceania|
Nicaragua|Managua|North America|
Niger|Niamey|Africa|
Nigeria|Abuja|Africa|
North Korea|Pyongyang|Asia|
North Macedonia|Skopje|Europe|Macedonia
Norway|Oslo|Europe|
Oman|Muscat|Asia|
Pakistan|Islamabad|Asia|
Palau|Ngerulmud|Oceania|
Palestine|Ramallah|Asia|State of Palestine
Panama|Panama City|North America|
Papua New Guinea|Port Moresby|Oceania|
Paraguay|Asuncion|South America|
Peru|Lima|South America|
Philippines|Manila|Asia|
Poland|Warsaw|Europe|
Portugal|Lisbon|Europe|
Qatar|Doha|Asia|
Romania|Bucharest|Europe|
Russia|Moscow|Europe|
Rwanda|Kigali|Africa|
Saint Kitts and Nevis|Basseterre|North America|St Kitts and Nevis
Saint Lucia|Castries|North America|St Lucia
Saint Vincent and the Grenadines|Kingstown|North America|St Vincent and the Grenadines
Samoa|Apia|Oceania|
San Marino|San Marino|Europe|
Sao Tome and Principe|Sao Tome|Africa|
Saudi Arabia|Riyadh|Asia|
Senegal|Dakar|Africa|
Serbia|Belgrade|Europe|
Seychelles|Victoria|Africa|
Sierra Leone|Freetown|Africa|
Singapore|Singapore|Asia|
Slovakia|Bratislava|Europe|
Slovenia|Ljubljana|Europe|
Solomon Islands|Honiara|Oceania|
Somalia|Mogadishu|Africa|
South Africa|Pretoria|Africa|
South Korea|Seoul|Asia|
South Sudan|Juba|Africa|
Spain|Madrid|Europe|
Sri Lanka|Sri Jayawardenepura Kotte|Asia|Ceylon
Sudan|Khartoum|Africa|
Suriname|Paramaribo|South America|
Sweden|Stockholm|Europe|
Switzerland|Bern|Europe|
Syria|Damascus|Asia|
Tajikistan|Dushanbe|Asia|
Tanzania|Dodoma|Africa|
Thailand|Bangkok|Asia|
Timor-Leste|Dili|Asia|East Timor
Togo|Lome|Africa|
Tonga|Nuku'alofa|Oceania|
Trinidad and Tobago|Port of Spain|North America|
Tunisia|Tunis|Africa|
Turkey|Ankara|Asia|Turkiye
Turkmenistan|Ashgabat|Asia|
Tuvalu|Funafuti|Oceania|
Uganda|Kampala|Africa|
Ukraine|Kyiv|Europe|Kiev
United Arab Emirates|Abu Dhabi|Asia|UAE
United Kingdom|London|Europe|UK;Great Britain;Britain
United States|Washington, D.C.|North America|United States of America;USA;US
Uruguay|Montevideo|South America|
Uzbekistan|Tashkent|Asia|
Vanuatu|Port Vila|Oceania|
Vatican City|Vatican City|Europe|Holy See
Venezuela|Caracas|South America|
Vietnam|Hanoi|Asia|Viet Nam
Yemen|Sanaa|Asia|
Zambia|Lusaka|Africa|
Zimbabwe|Harare|Africa|
"""


FAMOUS_COUNTRIES = {
    "Australia",
    "Brazil",
    "Canada",
    "China",
    "France",
    "Germany",
    "India",
    "Italy",
    "Japan",
    "Mexico",
    "Russia",
    "South Africa",
    "Spain",
    "United Kingdom",
    "United States",
}

OBSCURE_COUNTRIES = {
    "Andorra",
    "Antigua and Barbuda",
    "Benin",
    "Bhutan",
    "Brunei",
    "Burundi",
    "Comoros",
    "Djibouti",
    "Dominica",
    "Equatorial Guinea",
    "Kiribati",
    "Liechtenstein",
    "Marshall Islands",
    "Micronesia",
    "Nauru",
    "Palau",
    "Saint Kitts and Nevis",
    "Saint Vincent and the Grenadines",
    "San Marino",
    "Sao Tome and Principe",
    "Tuvalu",
    "Vanuatu",
}


US_STATE_ROWS = """
Alabama|Montgomery|South|7
Alaska|Juneau|West|8
Arizona|Phoenix|West|9
Arkansas|Little Rock|South|6
California|Sacramento|West|10
Colorado|Denver|West|9
Connecticut|Hartford|Northeast|7
Delaware|Dover|South|5
Florida|Tallahassee|South|10
Georgia|Atlanta|South|9
Hawaii|Honolulu|West|9
Idaho|Boise|West|6
Illinois|Springfield|Midwest|9
Indiana|Indianapolis|Midwest|8
Iowa|Des Moines|Midwest|6
Kansas|Topeka|Midwest|6
Kentucky|Frankfort|South|7
Louisiana|Baton Rouge|South|8
Maine|Augusta|Northeast|6
Maryland|Annapolis|South|8
Massachusetts|Boston|Northeast|9
Michigan|Lansing|Midwest|9
Minnesota|Saint Paul|Midwest|8|St Paul
Mississippi|Jackson|South|6
Missouri|Jefferson City|Midwest|8
Montana|Helena|West|6
Nebraska|Lincoln|Midwest|6
Nevada|Carson City|West|8
New Hampshire|Concord|Northeast|6
New Jersey|Trenton|Northeast|9
New Mexico|Santa Fe|West|7
New York|Albany|Northeast|10
North Carolina|Raleigh|South|9
North Dakota|Bismarck|Midwest|5
Ohio|Columbus|Midwest|9
Oklahoma|Oklahoma City|South|7
Oregon|Salem|West|8
Pennsylvania|Harrisburg|Northeast|9
Rhode Island|Providence|Northeast|6
South Carolina|Columbia|South|8
South Dakota|Pierre|Midwest|5
Tennessee|Nashville|South|8
Texas|Austin|South|10
Utah|Salt Lake City|West|8
Vermont|Montpelier|Northeast|5
Virginia|Richmond|South|9
Washington|Olympia|West|9
West Virginia|Charleston|South|6
Wisconsin|Madison|Midwest|8
Wyoming|Cheyenne|West|5
"""


UK_CITY_ROWS = """
Aberdeen|Scotland|9
Armagh|Northern Ireland|4
Bangor|Wales|5|bangor-wales|
Bangor|Northern Ireland|4|bangor-northern-ireland|Bangor NI
Bath|England|8
Belfast|Northern Ireland|9
Birmingham|England|10
Bradford|England|8
Brighton and Hove|England|9|brighton-and-hove|Brighton
Bristol|England|9
Cambridge|England|9
Canterbury|England|7
Cardiff|Wales|9
Carlisle|England|6
Chelmsford|England|6
Chester|England|7
Chichester|England|6
City of London|England|10|city-of-london|London
Colchester|England|6
Coventry|England|8
Derby|England|8
Derry|Northern Ireland|7|derry|Londonderry
Doncaster|England|6
Dundee|Scotland|8
Dunfermline|Scotland|5
Durham|England|7
Edinburgh|Scotland|10
Ely|England|5
Exeter|England|7
Glasgow|Scotland|10
Gloucester|England|7
Hereford|England|6
Inverness|Scotland|7
Kingston upon Hull|England|8|kingston-upon-hull|Hull
Lancaster|England|6
Leeds|England|9
Leicester|England|8
Lichfield|England|5
Lincoln|England|7
Lisburn|Northern Ireland|4
Liverpool|England|10
Manchester|England|10
Milton Keynes|England|8
Newcastle upon Tyne|England|9|newcastle-upon-tyne|Newcastle
Newport|Wales|7
Newry|Northern Ireland|5
Norwich|England|8
Nottingham|England|8
Oxford|England|9
Perth|Scotland|6
Peterborough|England|7
Plymouth|England|8
Portsmouth|England|8
Preston|England|7
Ripon|England|5
Salford|England|7
Salisbury|England|7
Sheffield|England|9
Southampton|England|8
Southend-on-Sea|England|7|southend-on-sea|Southend
St Albans|England|6|st-albans|Saint Albans
St Asaph|Wales|4|st-asaph|Saint Asaph
St Davids|Wales|4|st-davids|Saint Davids
Stirling|Scotland|7
Stoke-on-Trent|England|8
Sunderland|England|8
Swansea|Wales|8
Truro|England|5
Wakefield|England|7
Wells|England|5
Westminster|England|9
Winchester|England|7
Wolverhampton|England|8
Worcester|England|7
Wrexham|Wales|6
York|England|9
"""


PM_ROWS = """
Robert Walpole|1721|Whig|Robert Walpole
Spencer Compton, 1st Earl of Wilmington|1742|Whig|Earl of Wilmington;Spencer Compton
Henry Pelham|1743|Whig|
Thomas Pelham-Holles, 1st Duke of Newcastle|1754|Whig|Duke of Newcastle;Thomas Pelham-Holles
William Cavendish, 4th Duke of Devonshire|1756|Whig|Duke of Devonshire
John Stuart, 3rd Earl of Bute|1762|Tory|Earl of Bute;Lord Bute
George Grenville|1763|Whig|
Charles Watson-Wentworth, 2nd Marquess of Rockingham|1765|Whig|Rockingham;Lord Rockingham
William Pitt, 1st Earl of Chatham|1766|Whig|William Pitt the Elder;Earl of Chatham
Augustus FitzRoy, 3rd Duke of Grafton|1768|Whig|Duke of Grafton
Frederick North, Lord North|1770|Tory|Lord North
William Petty, 2nd Earl of Shelburne|1782|Whig|Earl of Shelburne;Lord Shelburne
William Cavendish-Bentinck, 3rd Duke of Portland|1783|Whig|Duke of Portland
William Pitt the Younger|1783|Tory|William Pitt
Henry Addington, 1st Viscount Sidmouth|1801|Tory|Henry Addington;Viscount Sidmouth
William Grenville, 1st Baron Grenville|1806|Whig|Lord Grenville;William Wyndham Grenville
Spencer Perceval|1809|Tory|
Robert Jenkinson, 2nd Earl of Liverpool|1812|Tory|Lord Liverpool;Earl of Liverpool;Robert Banks Jenkinson
George Canning|1827|Tory|
F. J. Robinson, 1st Viscount Goderich|1827|Tory|Frederick Robinson;Viscount Goderich;Lord Goderich
Arthur Wellesley, 1st Duke of Wellington|1828|Tory|Duke of Wellington;Wellington
Charles Grey, 2nd Earl Grey|1830|Whig|Earl Grey;Charles Grey
William Lamb, 2nd Viscount Melbourne|1834|Whig|Lord Melbourne;Viscount Melbourne
Robert Peel|1834|Conservative|Sir Robert Peel
John Russell, 1st Earl Russell|1846|Whig|Lord John Russell;Earl Russell
Edward Smith-Stanley, 14th Earl of Derby|1852|Conservative|Earl of Derby;Lord Derby
George Hamilton-Gordon, 4th Earl of Aberdeen|1852|Conservative|Earl of Aberdeen;Lord Aberdeen
Henry John Temple, 3rd Viscount Palmerston|1855|Whig|Lord Palmerston;Viscount Palmerston
Benjamin Disraeli|1868|Conservative|
William Ewart Gladstone|1868|Liberal|William Gladstone
Robert Gascoyne-Cecil, 3rd Marquess of Salisbury|1885|Conservative|Lord Salisbury;Marquess of Salisbury
Archibald Primrose, 5th Earl of Rosebery|1894|Liberal|Lord Rosebery;Earl of Rosebery
Arthur Balfour|1902|Conservative|
Henry Campbell-Bannerman|1905|Liberal|
H. H. Asquith|1908|Liberal|Herbert Asquith
David Lloyd George|1916|Liberal|Lloyd George
Bonar Law|1922|Conservative|
Stanley Baldwin|1923|Conservative|
Ramsay MacDonald|1924|Labour|
Neville Chamberlain|1937|Conservative|
Winston Churchill|1940|Conservative|
Clement Attlee|1945|Labour|
Anthony Eden|1955|Conservative|
Harold Macmillan|1957|Conservative|
Alec Douglas-Home|1963|Conservative|Douglas-Home;Lord Home
Harold Wilson|1964|Labour|
Edward Heath|1970|Conservative|Ted Heath
James Callaghan|1976|Labour|Jim Callaghan
Margaret Thatcher|1979|Conservative|
John Major|1990|Conservative|
Tony Blair|1997|Labour|
Gordon Brown|2007|Labour|
David Cameron|2010|Conservative|
Theresa May|2016|Conservative|
Boris Johnson|2019|Conservative|
Liz Truss|2022|Conservative|
Rishi Sunak|2022|Conservative|
Keir Starmer|2024|Labour|
"""


PRESIDENT_ROWS = """
George Washington|1789|None|10|
John Adams|1797|Federalist|8|
Thomas Jefferson|1801|Democratic-Republican|10|
James Madison|1809|Democratic-Republican|8|
James Monroe|1817|Democratic-Republican|8|
John Quincy Adams|1825|Democratic-Republican|7|J Q Adams
Andrew Jackson|1829|Democratic|9|
Martin Van Buren|1837|Democratic|7|
William Henry Harrison|1841|Whig|7|
John Tyler|1841|Whig|6|
James K. Polk|1845|Democratic|7|James Polk
Zachary Taylor|1849|Whig|7|
Millard Fillmore|1850|Whig|5|
Franklin Pierce|1853|Democratic|5|
James Buchanan|1857|Democratic|6|
Abraham Lincoln|1861|Republican|10|
Andrew Johnson|1865|Democratic|7|
Ulysses S. Grant|1869|Republican|9|Ulysses Grant
Rutherford B. Hayes|1877|Republican|5|Rutherford Hayes
James A. Garfield|1881|Republican|6|James Garfield
Chester A. Arthur|1881|Republican|5|Chester Arthur
Grover Cleveland|1885|Democratic|7|
Benjamin Harrison|1889|Republican|6|
William McKinley|1897|Republican|7|
Theodore Roosevelt|1901|Republican|10|Teddy Roosevelt
William Howard Taft|1909|Republican|8|William Taft
Woodrow Wilson|1913|Democratic|8|
Warren G. Harding|1921|Republican|6|Warren Harding
Calvin Coolidge|1923|Republican|7|
Herbert Hoover|1929|Republican|8|
Franklin D. Roosevelt|1933|Democratic|10|FDR;Franklin Roosevelt
Harry S. Truman|1945|Democratic|9|Harry Truman
Dwight D. Eisenhower|1953|Republican|10|Dwight Eisenhower;Ike
John F. Kennedy|1961|Democratic|10|JFK;John Kennedy
Lyndon B. Johnson|1963|Democratic|9|LBJ;Lyndon Johnson
Richard Nixon|1969|Republican|10|
Gerald Ford|1974|Republican|8|
Jimmy Carter|1977|Democratic|9|James Carter
Ronald Reagan|1981|Republican|10|
George H. W. Bush|1989|Republican|9|George Bush Senior;George Bush Sr
Bill Clinton|1993|Democratic|10|William Clinton
George W. Bush|2001|Republican|10|George Bush Junior;George Bush Jr
Barack Obama|2009|Democratic|10|
Donald Trump|2017|Republican|10|
Joe Biden|2021|Democratic|10|
"""


MONARCH_ROWS = """
William I|1066|Normandy|8|William the Conqueror
William II|1087|Normandy|5|William Rufus
Henry I|1100|Normandy|6|
Stephen|1135|Blois|6|King Stephen
Henry II|1154|Plantagenet|7|
Richard I|1189|Plantagenet|9|Richard the Lionheart
John|1199|Plantagenet|9|King John
Henry III|1216|Plantagenet|6|
Edward I|1272|Plantagenet|8|
Edward II|1307|Plantagenet|7|
Edward III|1327|Plantagenet|8|
Richard II|1377|Plantagenet|7|
Henry IV|1399|Lancaster|6|
Henry V|1413|Lancaster|8|
Henry VI|1422|Lancaster|7|
Edward IV|1461|York|7|
Edward V|1483|York|6|
Richard III|1483|York|9|
Henry VII|1485|Tudor|8|
Henry VIII|1509|Tudor|10|
Edward VI|1547|Tudor|7|
Mary I|1553|Tudor|8|Mary Tudor;Bloody Mary
Elizabeth I|1558|Tudor|10|
James I|1603|Stuart|8|James VI and I
Charles I|1625|Stuart|9|
Charles II|1660|Stuart|9|
James II|1685|Stuart|7|
William III|1689|Orange|7|William of Orange
Mary II|1689|Stuart|7|
Anne|1702|Stuart|8|Queen Anne
George I|1714|Hanover|7|
George II|1727|Hanover|7|
George III|1760|Hanover|9|
George IV|1820|Hanover|7|
William IV|1830|Hanover|6|
Victoria|1837|Hanover|10|Queen Victoria
Edward VII|1901|Saxe-Coburg and Gotha|8|
George V|1910|Windsor|8|
Edward VIII|1936|Windsor|9|
George VI|1936|Windsor|9|
Elizabeth II|1952|Windsor|10|
Charles III|2022|Windsor|10|
"""


def _make_elements() -> tuple[AnswerSpec, ...]:
    out: list[AnswerSpec] = []
    for row in _rows(ELEMENT_ROWS):
        atomic, symbol, name, family, fame, *alias_cols = row
        out.append(
            answer(
                name,
                aliases=_split_aliases(alias_cols[0]) if alias_cols else (),
                attrs={
                    "atomic_number": int(atomic),
                    "symbol": symbol,
                    "family": family,
                    "periodic_block": "f-block" if int(atomic) in range(57, 72) or int(atomic) in range(89, 104) else "",
                },
                wiki=wiki_url(f"{name}_(element)") if name in {"Mercury", "Lead"} else wiki_url(name),
                fame=int(fame),
            )
        )
    return tuple(out)


def _make_countries() -> tuple[AnswerSpec, ...]:
    out: list[AnswerSpec] = []
    for name, capital, continent, alias_col in _rows(COUNTRY_ROWS):
        fame = 5
        if name in FAMOUS_COUNTRIES:
            fame = 10
        elif name in OBSCURE_COUNTRIES:
            fame = 2
        elif continent in {"Oceania", "Africa"}:
            fame = 4
        out.append(
            answer(
                name,
                aliases=_split_aliases(alias_col),
                attrs={"capital": capital, "continent": continent},
                fame=fame,
            )
        )
    return tuple(out)


def _make_world_capitals(countries: tuple[AnswerSpec, ...]) -> tuple[AnswerSpec, ...]:
    out: list[AnswerSpec] = []
    for country in countries:
        capital = str(country.attrs["capital"])
        out.append(
            answer(
                capital,
                id=f"{slugify(country.name)}-capital",
                aliases=(),
                attrs={"country": country.name, "continent": country.attrs["continent"]},
                fame=max(2, country.fame - 1),
                wiki=wiki_url(capital),
            )
        )
    return tuple(out)


def _make_us_states() -> tuple[AnswerSpec, ...]:
    out: list[AnswerSpec] = []
    for row in _rows(US_STATE_ROWS):
        state, capital, region, fame, *alias_cols = row
        out.append(
            answer(
                state,
                aliases=(),
                attrs={"capital": capital, "region": region},
                fame=int(fame),
            )
        )
    return tuple(out)


def _make_us_state_capitals(states: tuple[AnswerSpec, ...]) -> tuple[AnswerSpec, ...]:
    out: list[AnswerSpec] = []
    for state in states:
        capital = str(state.attrs["capital"])
        aliases = _split_aliases("St Paul") if capital == "Saint Paul" else ()
        out.append(
            answer(
                capital,
                id=f"{slugify(state.name)}-capital",
                aliases=aliases,
                attrs={"state": state.name, "region": state.attrs["region"]},
                fame=max(2, state.fame - 1),
                wiki=wiki_url(capital),
            )
        )
    return tuple(out)


def _make_uk_cities() -> tuple[AnswerSpec, ...]:
    out: list[AnswerSpec] = []
    for row in _rows(UK_CITY_ROWS):
        name, nation, fame, *rest = row
        explicit_id = rest[0] if len(rest) > 0 and rest[0] else None
        aliases = _split_aliases(rest[1]) if len(rest) > 1 else ()
        out.append(
            answer(
                name,
                aliases=aliases,
                id=explicit_id,
                attrs={"nation": nation},
                fame=int(fame),
            )
        )
    return tuple(out)


def _make_pm_answers() -> tuple[AnswerSpec, ...]:
    out: list[AnswerSpec] = []
    for name, year_s, party, aliases in _rows(PM_ROWS):
        year = int(year_s)
        fame = 5
        if year >= 1940:
            fame = 8
        if name in {"Winston Churchill", "Margaret Thatcher", "Tony Blair", "Boris Johnson", "Keir Starmer"}:
            fame = 10
        if "Earl" in name or "Duke" in name or "Viscount" in name or "Marquess" in name:
            fame = min(fame, 4)
        out.append(
            answer(
                name,
                aliases=_split_aliases(aliases),
                attrs={"first_served": year, "century": _century(year), "party": party},
                fame=fame,
            )
        )
    return tuple(out)


def _make_president_answers() -> tuple[AnswerSpec, ...]:
    out: list[AnswerSpec] = []
    for name, year_s, party, fame, aliases in _rows(PRESIDENT_ROWS):
        year = int(year_s)
        out.append(
            answer(
                name,
                aliases=_split_aliases(aliases),
                attrs={"first_served": year, "century": _century(year), "party": party},
                fame=int(fame),
            )
        )
    return tuple(out)


def _make_monarch_answers() -> tuple[AnswerSpec, ...]:
    out: list[AnswerSpec] = []
    for name, year_s, house, fame, aliases in _rows(MONARCH_ROWS):
        year = int(year_s)
        out.append(
            answer(
                name,
                aliases=_split_aliases(aliases),
                attrs={"reign_start": year, "century": _century(year), "house": house},
                fame=int(fame),
            )
        )
    return tuple(out)


ELEMENT_QUESTION_TEMPLATES = COMMON_NAME_TEMPLATES + (
    {
        "id": "elements-consonant",
        "kind": "starts_with_consonant",
        "field": "name",
        "prompt": "Elements of the periodic table whose name begins with a consonant",
    },
    {
        "id": "elements-first-vowel-i",
        "kind": "first_vowel",
        "field": "name",
        "value": "i",
        "prompt": "Chemical elements whose first vowel is I",
    },
    {
        "id": "elements-atomic-57-71",
        "kind": "number_range",
        "attr": "atomic_number",
        "min": 57,
        "max": 71,
        "prompt": "Chemical elements with atomic numbers from 57 to 71",
    },
    {
        "id": "elements-symbol-one-letter",
        "kind": "text_length",
        "attr": "symbol",
        "value": 1,
        "prompt": "Chemical elements with a one-letter symbol",
    },
)


COUNTRY_QUESTION_TEMPLATES = COMMON_NAME_TEMPLATES + (
    {
        "id": "countries-by-continent",
        "kind": "attr_equals_dynamic",
        "attr": "continent",
        "prompt": "Countries in {value}",
    },
    {
        "id": "countries-capital-same-initial",
        "kind": "same_initial",
        "field": "name",
        "attr": "capital",
        "prompt": "Countries whose capital city starts with the same letter as the country",
    },
)


CAPITAL_QUESTION_TEMPLATES = COMMON_NAME_TEMPLATES + (
    {
        "id": "capitals-by-continent",
        "kind": "attr_equals_dynamic",
        "attr": "continent",
        "prompt": "Capital cities of countries in {value}",
    },
    {
        "id": "capitals-same-country-initial",
        "kind": "same_initial",
        "field": "name",
        "attr": "country",
        "prompt": "Capital cities starting with the same letter as their country",
    },
)


STATE_CAPITAL_QUESTION_TEMPLATES = COMMON_NAME_TEMPLATES + (
    {
        "id": "state-capitals-containing-state",
        "kind": "contains_any_letters",
        "field": "name",
        "letters": "STATE",
        "prompt": "US state capitals containing at least one of the letters S, T, A, T or E",
    },
    {
        "id": "state-capitals-same-state-initial",
        "kind": "same_initial",
        "field": "name",
        "attr": "state",
        "prompt": "US state capitals starting with the same letter as their state",
    },
    {
        "id": "state-capitals-by-region",
        "kind": "attr_equals_dynamic",
        "attr": "region",
        "prompt": "US state capitals in {value} states",
    },
)


LEADER_QUESTION_TEMPLATES = COMMON_NAME_TEMPLATES + (
    {
        "id": "leaders-by-century",
        "kind": "attr_equals_dynamic",
        "attr": "century",
        "prompt": "{category} who first served in the {value}",
    },
    {
        "id": "leaders-after-1900",
        "kind": "number_range",
        "attr": "first_served",
        "min": 1900,
        "max": 2100,
        "prompt": "{category} who first served from 1900 onwards",
    },
)


MONARCH_QUESTION_TEMPLATES = COMMON_NAME_TEMPLATES + (
    {
        "id": "monarchs-by-house",
        "kind": "attr_equals_dynamic",
        "attr": "house",
        "prompt": "English or British monarchs from the House of {value}",
    },
    {
        "id": "monarchs-before-1600",
        "kind": "number_range",
        "attr": "reign_start",
        "min": 1066,
        "max": 1599,
        "prompt": "English monarchs whose reign began before 1600",
    },
)


COUNTRIES = _make_countries()
US_STATES = _make_us_states()


CATEGORY_LIST: tuple[CategorySpec, ...] = (
    CategorySpec(
        slug="chemical-elements",
        name="Chemical Elements",
        description="The 118 named chemical elements of the periodic table.",
        tags=("science", "recurring", "finite"),
        answer_kind="element",
        expected_count=118,
        display_fields=("symbol", "atomic_number", "family"),
        question_templates=ELEMENT_QUESTION_TEMPLATES,
        answers=_make_elements(),
        sources=({"label": "IUPAC periodic table", "url": "https://iupac.org/what-we-do/periodic-table-of-elements/"},),
    ),
    CategorySpec(
        slug="countries",
        name="Countries",
        description="UN member states plus the two UN observer states, using common English names.",
        tags=("geography", "recurring", "finite"),
        answer_kind="country",
        expected_count=195,
        display_fields=("capital", "continent"),
        question_templates=COUNTRY_QUESTION_TEMPLATES,
        answers=COUNTRIES,
        sources=({"label": "United Nations member states", "url": "https://www.un.org/en/about-us/member-states"},),
    ),
    CategorySpec(
        slug="world-capitals",
        name="World Capitals",
        description="Capital cities for the countries fixture, using one quiz-friendly capital per country.",
        tags=("geography", "capitals", "recurring"),
        answer_kind="capital",
        expected_count=195,
        display_fields=("country", "continent"),
        question_templates=CAPITAL_QUESTION_TEMPLATES,
        answers=_make_world_capitals(COUNTRIES),
        sources=({"label": "Country fixture capitals", "url": "https://www.un.org/en/about-us/member-states"},),
    ),
    CategorySpec(
        slug="uk-prime-ministers",
        name="UK Prime Ministers",
        description="People who have served as Prime Minister of Great Britain or the United Kingdom, Walpole to Starmer.",
        tags=("history", "politics", "recurring"),
        answer_kind="prime minister",
        expected_count=58,
        display_fields=("first_served", "party"),
        question_templates=LEADER_QUESTION_TEMPLATES,
        answers=_make_pm_answers(),
        sources=({"label": "GOV.UK Prime Minister role", "url": "https://www.gov.uk/government/ministers/prime-minister"},),
    ),
    CategorySpec(
        slug="us-presidents",
        name="US Presidents",
        description="The 45 people who have served as President of the United States, counting non-consecutive terms once.",
        tags=("history", "politics", "recurring"),
        answer_kind="president",
        expected_count=45,
        display_fields=("first_served", "party"),
        question_templates=LEADER_QUESTION_TEMPLATES,
        answers=_make_president_answers(),
        sources=({"label": "The White House presidents", "url": "https://www.whitehouse.gov/about-the-white-house/presidents/"},),
    ),
    CategorySpec(
        slug="us-states",
        name="US States",
        description="The 50 states of the United States.",
        tags=("geography", "usa", "recurring"),
        answer_kind="state",
        expected_count=50,
        display_fields=("capital", "region"),
        question_templates=COUNTRY_QUESTION_TEMPLATES,
        answers=US_STATES,
        sources=({"label": "USA.gov state governments", "url": "https://www.usa.gov/states-and-territories"},),
    ),
    CategorySpec(
        slug="us-state-capitals",
        name="US State Capitals",
        description="The capital city of each US state.",
        tags=("geography", "usa", "capitals", "recurring"),
        answer_kind="state capital",
        expected_count=50,
        display_fields=("state", "region"),
        question_templates=STATE_CAPITAL_QUESTION_TEMPLATES,
        answers=_make_us_state_capitals(US_STATES),
        sources=({"label": "USA.gov state governments", "url": "https://www.usa.gov/states-and-territories"},),
    ),
    CategorySpec(
        slug="uk-cities",
        name="UK Cities",
        description="UK places with official city status, including the 2022 Platinum Jubilee cities.",
        tags=("geography", "uk", "recurring"),
        answer_kind="city",
        expected_count=76,
        display_fields=("nation",),
        question_templates=COMMON_NAME_TEMPLATES
        + (
            {
                "id": "uk-cities-by-nation",
                "kind": "attr_equals_dynamic",
                "attr": "nation",
                "prompt": "UK cities in {value}",
            },
        ),
        answers=_make_uk_cities(),
        sources=({"label": "UK city status", "url": "https://www.gov.uk/government/publications/list-of-cities/list-of-cities-html"},),
    ),
    CategorySpec(
        slug="english-british-monarchs",
        name="English and British Monarchs",
        description="English and British monarchs from 1066 to Charles III, excluding disputed claimants.",
        tags=("history", "monarchy", "recurring"),
        answer_kind="monarch",
        expected_count=42,
        display_fields=("reign_start", "house"),
        question_templates=MONARCH_QUESTION_TEMPLATES,
        answers=_make_monarch_answers(),
        sources=({"label": "Royal Family kings and queens", "url": "https://www.royal.uk/kings-and-queens-1066"},),
    ),
)


CATEGORIES: dict[str, CategorySpec] = {category.slug: category for category in CATEGORY_LIST}

# Backwards-compatible name for older imports; new code should use CategorySpec.
Category = CategorySpec
