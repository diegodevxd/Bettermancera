-- Corrección de precios con un solo precio claro en el PDF
-- Basado en Catálogo Julio 2026.pdf
-- Ejecutar en Supabase SQL Editor

-- 26021 Set Dispensa Vitrolux: actual 1300/599 -> PDF 1300/1300
UPDATE public.productos SET precio_regular = 1300, precio_oferta = 1300 WHERE codigo = '26021';

-- 26995 Fácil Mop: actual 850/559 -> PDF 850/850
UPDATE public.productos SET precio_regular = 850, precio_oferta = 850 WHERE codigo = '26995';

-- 26793 Repisa Oslo: actual 700/499 -> PDF 700/700
UPDATE public.productos SET precio_regular = 700, precio_oferta = 700 WHERE codigo = '26793';

-- 26749 Deco Macetero: actual 900/750 -> PDF 750/750
UPDATE public.productos SET precio_regular = 750, precio_oferta = 750 WHERE codigo = '26749';

-- 26712 Set Mesas Álamo: actual 900/750 -> PDF 900/900
UPDATE public.productos SET precio_regular = 900, precio_oferta = 900 WHERE codigo = '26712';

-- 24409 Rack Slim Bambú: actual 950/800 -> PDF 800/800
UPDATE public.productos SET precio_regular = 800, precio_oferta = 800 WHERE codigo = '24409';

-- 26750 Deco Orquidea Coral: actual 249/139 -> PDF 249/249
UPDATE public.productos SET precio_regular = 249, precio_oferta = 249 WHERE codigo = '26750';

-- 25342 Repi Llavero: actual 249/139 -> PDF 139/139
UPDATE public.productos SET precio_regular = 139, precio_oferta = 139 WHERE codigo = '25342';

-- 24791 Lámpara: actual 449/129 -> PDF 449/449
UPDATE public.productos SET precio_regular = 449, precio_oferta = 449 WHERE codigo = '24791';

-- 24771 Luz Sensor Slim: actual 159/149 -> PDF 159/159
UPDATE public.productos SET precio_regular = 159, precio_oferta = 159 WHERE codigo = '24771';

-- 25774 Citro Repel Mosquitos: actual 5490/169 -> PDF 169/169
UPDATE public.productos SET precio_regular = 169, precio_oferta = 169 WHERE codigo = '25774';

-- 26786 Maxi Mata Moscas: actual 5490/169 -> PDF 54.9/54.9
UPDATE public.productos SET precio_regular = 54.9, precio_oferta = 54.9 WHERE codigo = '26786';

-- 26878 Tulipán Solar: actual 209/179 -> PDF 209/209
UPDATE public.productos SET precio_regular = 209, precio_oferta = 209 WHERE codigo = '26878';

-- 25789 Tapete Media Luna: actual 209/179 -> PDF 179/179
UPDATE public.productos SET precio_regular = 179, precio_oferta = 179 WHERE codigo = '25789';

-- 26732 Cuadri Espejos: actual 7990/149 -> PDF 149/149
UPDATE public.productos SET precio_regular = 149, precio_oferta = 149 WHERE codigo = '26732';

-- 26708 Flor Multi Color: actual 8990/7990 -> PDF 89.9/89.9
UPDATE public.productos SET precio_regular = 89.9, precio_oferta = 89.9 WHERE codigo = '26708';

-- 25854 Set Cuelga Fácil: actual 8990/7990 -> PDF 79.9/79.9
UPDATE public.productos SET precio_regular = 79.9, precio_oferta = 79.9 WHERE codigo = '25854';

-- 24859 Tapete Champagne: actual 699/649 -> PDF 699/699
UPDATE public.productos SET precio_regular = 699, precio_oferta = 699 WHERE codigo = '24859';

-- 26716 Multi Organizador B: actual 5990/5990 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '26716';

-- 24245 Multi Contacto Roll: actual 5990/299 -> PDF 299/299
UPDATE public.productos SET precio_regular = 299, precio_oferta = 299 WHERE codigo = '24245';

-- 25141 Better Contacto Pro: actual 299/199 -> PDF 199/199
UPDATE public.productos SET precio_regular = 199, precio_oferta = 199 WHERE codigo = '25141';

-- 21750 Guarda Clima: actual 5490/229 -> PDF 229/229
UPDATE public.productos SET precio_regular = 229, precio_oferta = 229 WHERE codigo = '21750';

-- 26879 Adherible 3D Laja: actual 139/139 -> PDF 279/279
UPDATE public.productos SET precio_regular = 279, precio_oferta = 279 WHERE codigo = '26879';

-- 25383 Adherible Cantera: actual 279/189 -> PDF 189/189
UPDATE public.productos SET precio_regular = 189, precio_oferta = 189 WHERE codigo = '25383';

-- 25467 Textur Ladrillo: actual 209/179 -> PDF 209/209
UPDATE public.productos SET precio_regular = 209, precio_oferta = 209 WHERE codigo = '25467';

-- 25576 Adherible Panel Madera: actual 189/149 -> PDF 189/189
UPDATE public.productos SET precio_regular = 189, precio_oferta = 189 WHERE codigo = '25576';

-- 26327 Maxi Zapatera Protect: actual 900/599 -> PDF 900/900
UPDATE public.productos SET precio_regular = 900, precio_oferta = 900 WHERE codigo = '26327';

-- 26324 Cubo Fundas Marino: actual 329/299 -> PDF 299/299
UPDATE public.productos SET precio_regular = 299, precio_oferta = 299 WHERE codigo = '26324';

-- 26322 Cesto Marino: actual 329/299 -> PDF 329/329
UPDATE public.productos SET precio_regular = 329, precio_oferta = 329 WHERE codigo = '26322';

-- 25300 Set Bolsas Compress: actual 159/139 -> PDF 159/159
UPDATE public.productos SET precio_regular = 159, precio_oferta = 159 WHERE codigo = '25300';

-- 26312 Triangu Cesto: actual 199/179 -> PDF 179/179
UPDATE public.productos SET precio_regular = 179, precio_oferta = 179 WHERE codigo = '26312';

-- 25979 Organi Gorras: actual 5990/109 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '25979';

-- 25981 Absorbe Humedad: actual 8990/5990 -> PDF 89.9/89.9
UPDATE public.productos SET precio_regular = 89.9, precio_oferta = 89.9 WHERE codigo = '25981';

-- 25869 Funda Prendas Protect: actual 159/129 -> PDF 159/159
UPDATE public.productos SET precio_regular = 159, precio_oferta = 159 WHERE codigo = '25869';

-- 25556 Sartén Carbón-Pro: actual 579/499 -> PDF 499/499
UPDATE public.productos SET precio_regular = 499, precio_oferta = 499 WHERE codigo = '25556';

-- 24526 Fryer Dúo Lux: actual 3400/259 -> PDF 3400/3400
UPDATE public.productos SET precio_regular = 3400, precio_oferta = 3400 WHERE codigo = '24526';

-- 26537 Espátula Rinde Dúo: actual 5490/3400 -> PDF 54.9/54.9
UPDATE public.productos SET precio_regular = 54.9, precio_oferta = 54.9 WHERE codigo = '26537';

-- 26563 Aceitera Deluxe: actual 5490/169 -> PDF 169/169
UPDATE public.productos SET precio_regular = 169, precio_oferta = 169 WHERE codigo = '26563';

-- 26553 Escurre Bowl: actual 9990/9990 -> PDF 99.9/99.9
UPDATE public.productos SET precio_regular = 99.9, precio_oferta = 99.9 WHERE codigo = '26553';

-- 25569 Soporte Utensilios Flora: actual 229/229 -> PDF 49.9/49.9
UPDATE public.productos SET precio_regular = 49.9, precio_oferta = 49.9 WHERE codigo = '25569';

-- 26534 Chopper Pro: actual 219/189 -> PDF 219/219
UPDATE public.productos SET precio_regular = 219, precio_oferta = 219 WHERE codigo = '26534';

-- 26514 Multi Rallador Pro: actual 219/189 -> PDF 189/189
UPDATE public.productos SET precio_regular = 189, precio_oferta = 189 WHERE codigo = '26514';

-- 21540 Multi Pelador Chef: actual 5490/119 -> PDF 54.9/54.9
UPDATE public.productos SET precio_regular = 54.9, precio_oferta = 54.9 WHERE codigo = '21540';

-- 23531 Corta Manzanas Pro: actual 5490/119 -> PDF 119/119
UPDATE public.productos SET precio_regular = 119, precio_oferta = 119 WHERE codigo = '23531';

-- 26540 Gira Pelador: actual 5490/119 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '26540';

-- 23516 Tri Afilador: actual 159/129 -> PDF 159/159
UPDATE public.productos SET precio_regular = 159, precio_oferta = 159 WHERE codigo = '23516';

-- 25530 Afila Cuchillo: actual 159/149 -> PDF 149/149
UPDATE public.productos SET precio_regular = 149, precio_oferta = 149 WHERE codigo = '25530';

-- 23543 Tijeras Chef: actual 159/149 -> PDF 64.9/64.9
UPDATE public.productos SET precio_regular = 64.9, precio_oferta = 64.9 WHERE codigo = '23543';

-- 26802 Condimentos Lux: actual 9990/9990 -> PDF 99.9/99.9
UPDATE public.productos SET precio_regular = 99.9, precio_oferta = 99.9 WHERE codigo = '26802';

-- 26549 Cuadri Tablas: actual 7990/159 -> PDF 79.9/79.9
UPDATE public.productos SET precio_regular = 79.9, precio_oferta = 79.9 WHERE codigo = '26549';

-- 26564 Practi Escurre: actual 7490/229 -> PDF 229/229
UPDATE public.productos SET precio_regular = 229, precio_oferta = 229 WHERE codigo = '26564';

-- 26531 Tapa Micro Pro: actual 7490/229 -> PDF 74.9/74.9
UPDATE public.productos SET precio_regular = 74.9, precio_oferta = 74.9 WHERE codigo = '26531';

-- 25560 Frutero Black: actual 379/259 -> PDF 379/379
UPDATE public.productos SET precio_regular = 379, precio_oferta = 379 WHERE codigo = '25560';

-- 26803 Frutero Black: actual 479/379 -> PDF 479/479
UPDATE public.productos SET precio_regular = 479, precio_oferta = 479 WHERE codigo = '26803';

-- 26836 Set Sujeti Ganchos: actual 5990/169 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '26836';

-- 26844 Charola escurridora: actual 549/399 -> PDF 399/399
UPDATE public.productos SET precio_regular = 399, precio_oferta = 399 WHERE codigo = '26844';

-- 24039 Dúo Escurridor Black: actual 549/399 -> PDF 549/549
UPDATE public.productos SET precio_regular = 549, precio_oferta = 549 WHERE codigo = '24039';

-- 25060 Organi Canastilla Fregadero: actual 5990/5990 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '25060';

-- 26048 Organi: actual 5990/149 -> PDF 149/149
UPDATE public.productos SET precio_regular = 149, precio_oferta = 149 WHERE codigo = '26048';

-- 23566 Eco Push: actual 179/129 -> PDF 129/129
UPDATE public.productos SET precio_regular = 129, precio_oferta = 129 WHERE codigo = '23566';

-- 25049 Canastilla Dúo Protect: actual 6990/6990 -> PDF 69.9/69.9
UPDATE public.productos SET precio_regular = 69.9, precio_oferta = 69.9 WHERE codigo = '25049';

-- 26990 Escurritapete Jumbo: actual 6990/199 -> PDF 199/199
UPDATE public.productos SET precio_regular = 199, precio_oferta = 199 WHERE codigo = '26990';

-- 21027 Eco Repisa Escalonada: actual 179/109 -> PDF 109/109
UPDATE public.productos SET precio_regular = 109, precio_oferta = 109 WHERE codigo = '21027';

-- 26528 Sartenes Dúo: actual 179/109 -> PDF 179/179
UPDATE public.productos SET precio_regular = 179, precio_oferta = 179 WHERE codigo = '26528';

-- 25059 Desli Organi Utensilios: actual 4990/179 -> PDF 49.9/49.9
UPDATE public.productos SET precio_regular = 49.9, precio_oferta = 49.9 WHERE codigo = '25059';

-- 26800 Porta Rollos Klin: actual 129/109 -> PDF 109/109
UPDATE public.productos SET precio_regular = 109, precio_oferta = 109 WHERE codigo = '26800';

-- 25808 Porta Rollo Granito: actual 129/109 -> PDF 129/129
UPDATE public.productos SET precio_regular = 129, precio_oferta = 129 WHERE codigo = '25808';

-- 24821 Protecti Tapete: actual 7990/129 -> PDF 79.9/79.9
UPDATE public.productos SET precio_regular = 79.9, precio_oferta = 79.9 WHERE codigo = '24821';

-- 21014 Banco Plegable: actual 7990/319 -> PDF 319/319
UPDATE public.productos SET precio_regular = 319, precio_oferta = 319 WHERE codigo = '21014';

-- 24160 Deslisalsa: actual 149/109 -> PDF 109/109
UPDATE public.productos SET precio_regular = 109, precio_oferta = 109 WHERE codigo = '24160';

-- 26028 Papitas Clip: actual 5490/5490 -> PDF 54.9/54.9
UPDATE public.productos SET precio_regular = 54.9, precio_oferta = 54.9 WHERE codigo = '26028';

-- 26044 Esfera Bowls: actual 5490/229 -> PDF 229/229
UPDATE public.productos SET precio_regular = 229, precio_oferta = 229 WHERE codigo = '26044';

-- 26515 Gelati Flor: actual 229/159 -> PDF 159/159
UPDATE public.productos SET precio_regular = 159, precio_oferta = 159 WHERE codigo = '26515';

-- 24880 Organi Blanquillos: actual 249/109 -> PDF 109/109
UPDATE public.productos SET precio_regular = 109, precio_oferta = 109 WHERE codigo = '24880';

-- 25465 Canasta Dúo Fresh: actual 299/279 -> PDF 279/279
UPDATE public.productos SET precio_regular = 279, precio_oferta = 279 WHERE codigo = '25465';

-- 25064 Set Cerealeros Max: actual 900/399 -> PDF 399/399
UPDATE public.productos SET precio_regular = 399, precio_oferta = 399 WHERE codigo = '25064';

-- 24155 Better Purificador: actual 1200/600 -> PDF 1200/1200
UPDATE public.productos SET precio_regular = 1200, precio_oferta = 1200 WHERE codigo = '24155';

-- 26874 Gurmy Nutri Dúo: actual 5990/219 -> PDF 219/219
UPDATE public.productos SET precio_regular = 219, precio_oferta = 219 WHERE codigo = '26874';

-- 25000 Gurmy Quesadilla Conmigo: actual 5990/219 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '25000';

-- 26908 Gurmy Porciones: actual 5990/129 -> PDF 129/129
UPDATE public.productos SET precio_regular = 129, precio_oferta = 129 WHERE codigo = '26908';

-- 26873 Gurmay Pizza: actual 149/139 -> PDF 139/139
UPDATE public.productos SET precio_regular = 139, precio_oferta = 139 WHERE codigo = '26873';

-- 26053 Lunch Pack: actual 149/139 -> PDF 149/149
UPDATE public.productos SET precio_regular = 149, precio_oferta = 149 WHERE codigo = '26053';

-- 26001 Gurmy Econo Pack: actual 149/139 -> PDF 99.9/99.9
UPDATE public.productos SET precio_regular = 99.9, precio_oferta = 99.9 WHERE codigo = '26001';

-- 26993 Gurmy Porciones Value Pack: actual 9990/149 -> PDF 189.16/189.16
UPDATE public.productos SET precio_regular = 189.16, precio_oferta = 189.16 WHERE codigo = '26993';

-- 25053 Gurmy Set Lunch Max: actual 449/199 -> PDF 449/449
UPDATE public.productos SET precio_regular = 449, precio_oferta = 449 WHERE codigo = '25053';

-- 20038 Circulock: actual 449/199 -> PDF 199/199
UPDATE public.productos SET precio_regular = 199, precio_oferta = 199 WHERE codigo = '20038';

-- 26016 Gurmy: actual 449/199 -> PDF 169/169
UPDATE public.productos SET precio_regular = 169, precio_oferta = 169 WHERE codigo = '26016';

-- 24619 Jamón Lockit Max: actual 199/169 -> PDF 74.9/74.9
UPDATE public.productos SET precio_regular = 74.9, precio_oferta = 74.9 WHERE codigo = '24619';

-- 24074 Salchichas Lockit Max: actual 7490/119 -> PDF 74.9/74.9
UPDATE public.productos SET precio_regular = 74.9, precio_oferta = 74.9 WHERE codigo = '24074';

-- 26025 Conserva Mantequilla: actual 7490/6990 -> PDF 69.9/69.9
UPDATE public.productos SET precio_regular = 69.9, precio_oferta = 69.9 WHERE codigo = '26025';

-- 25047 Gurmy Conserva: actual 6990/5990 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '25047';

-- 25052 Conserva Cebolla: actual 5990/5990 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '25052';

-- 25028 Destapador: actual 9990/9990 -> PDF 99.9/99.9
UPDATE public.productos SET precio_regular = 99.9, precio_oferta = 99.9 WHERE codigo = '25028';

-- 21525 Marcianitos Pop: actual 9990/129 -> PDF 129/129
UPDATE public.productos SET precio_regular = 129, precio_oferta = 129 WHERE codigo = '21525';

-- 26054 Gurmy Toy Story: actual 249/129 -> PDF 249/249
UPDATE public.productos SET precio_regular = 249, precio_oferta = 249 WHERE codigo = '26054';

-- 26778 Lonchera Toy Story: actual 399/249 -> PDF 399/399
UPDATE public.productos SET precio_regular = 399, precio_oferta = 399 WHERE codigo = '26778';

-- 26703 Lonchera Box: actual 199/119 -> PDF 199/199
UPDATE public.productos SET precio_regular = 199, precio_oferta = 199 WHERE codigo = '26703';

-- 26245 Set Floral: actual 8990/249 -> PDF 249/249
UPDATE public.productos SET precio_regular = 249, precio_oferta = 249 WHERE codigo = '26245';

-- 26997 Tina Plegable Masaje: actual 269/269 -> PDF 649/649
UPDATE public.productos SET precio_regular = 649, precio_oferta = 649 WHERE codigo = '26997';

-- 24212 Pedi Spa Smart: actual 950/199 -> PDF 950/950
UPDATE public.productos SET precio_regular = 950, precio_oferta = 950 WHERE codigo = '24212';

-- 26882 Barras Pedi Spa Lavanda + Frutal: actual 950/199 -> PDF 199/199
UPDATE public.productos SET precio_regular = 199, precio_oferta = 199 WHERE codigo = '26882';

-- 26401 Removible Lupa: actual 449/219 -> PDF 449/449
UPDATE public.productos SET precio_regular = 449, precio_oferta = 449 WHERE codigo = '26401';

-- 26224 Practi: actual 449/219 -> PDF 219/219
UPDATE public.productos SET precio_regular = 219, precio_oferta = 219 WHERE codigo = '26224';

-- 26236 Corta Uñas Zoom: actual 7990/7990 -> PDF 79.9/79.9
UPDATE public.productos SET precio_regular = 79.9, precio_oferta = 79.9 WHERE codigo = '26236';

-- 26767 Maxi Cepillo Klin: actual 5990/169 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '26767';

-- 26243 Parches Aloe: actual 9990/9990 -> PDF 99.9/99.9
UPDATE public.productos SET precio_regular = 99.9, precio_oferta = 99.9 WHERE codigo = '26243';

-- 26229 Spa Facial Magic: actual 359/299 -> PDF 359/359
UPDATE public.productos SET precio_regular = 359, precio_oferta = 359 WHERE codigo = '26229';

-- 25217 Bye Vello Pro: actual 359/299 -> PDF 299/299
UPDATE public.productos SET precio_regular = 299, precio_oferta = 299 WHERE codigo = '25217';

-- 26242 Medias: actual 449/149 -> PDF 149/149
UPDATE public.productos SET precio_regular = 149, precio_oferta = 149 WHERE codigo = '26242';

-- 26233 Antifaz Maxi Confort: actual 5990/249 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '26233';

-- 23306 Almohada Multi Confort: actual 5990/249 -> PDF 249/249
UPDATE public.productos SET precio_regular = 249, precio_oferta = 249 WHERE codigo = '23306';

-- 26228 Almohada Air Confort: actual 5990/249 -> PDF 399/399
UPDATE public.productos SET precio_regular = 399, precio_oferta = 399 WHERE codigo = '26228';

-- 26419 Set Baño Essencial: actual 299/199 -> PDF 299/299
UPDATE public.productos SET precio_regular = 299, precio_oferta = 299 WHERE codigo = '26419';

-- 26300 Cestos Lux: actual 219/159 -> PDF 219/219
UPDATE public.productos SET precio_regular = 219, precio_oferta = 219 WHERE codigo = '26300';

-- 26412 Cinta Anti Caídas Max: actual 4990/199 -> PDF 49.9/49.9
UPDATE public.productos SET precio_regular = 49.9, precio_oferta = 49.9 WHERE codigo = '26412';

-- 21423 Renova Juntas: actual 6990/6990 -> PDF 69.9/69.9
UPDATE public.productos SET precio_regular = 69.9, precio_oferta = 69.9 WHERE codigo = '21423';

-- 26410 Porta Rollo Slim: actual 169/119 -> PDF 169/169
UPDATE public.productos SET precio_regular = 169, precio_oferta = 169 WHERE codigo = '26410';

-- 25444 Atrapa Cabellos Dúo: actual 5990/5990 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '25444';

-- 23432 Protecti Desagüe Max: actual 5990/3490 -> PDF 34.9/34.9
UPDATE public.productos SET precio_regular = 34.9, precio_oferta = 34.9 WHERE codigo = '23432';

-- 25439 Modu Caddy: actual 299/169 -> PDF 169/169
UPDATE public.productos SET precio_regular = 169, precio_oferta = 169 WHERE codigo = '25439';

-- 26405 Caddy Black: actual 269/169 -> PDF 269/269
UPDATE public.productos SET precio_regular = 269, precio_oferta = 269 WHERE codigo = '26405';

-- 26135 Set Barre Fácil: actual 700/459 -> PDF 700/700
UPDATE public.productos SET precio_regular = 700, precio_oferta = 700 WHERE codigo = '26135';

-- 23121 Esquina Practiklin: actual 369/299 -> PDF 369/369
UPDATE public.productos SET precio_regular = 369, precio_oferta = 369 WHERE codigo = '23121';

-- 24110 Cepi Prendas: actual 5990/159 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '24110';

-- 26119 Lava Bra Flex: actual 8990/5990 -> PDF 89.9/89.9
UPDATE public.productos SET precio_regular = 89.9, precio_oferta = 89.9 WHERE codigo = '26119';

-- 26112 Funda Lavadora Platina: actual 8990/299 -> PDF 299/299
UPDATE public.productos SET precio_regular = 299, precio_oferta = 299 WHERE codigo = '26112';

-- 25126 Exten Lavadero: actual 7990/109 -> PDF 79.9/79.9
UPDATE public.productos SET precio_regular = 79.9, precio_oferta = 79.9 WHERE codigo = '25126';

-- 26111 Lava Tenis Max: actual 7990/6990 -> PDF 69.9/69.9
UPDATE public.productos SET precio_regular = 69.9, precio_oferta = 69.9 WHERE codigo = '26111';

-- 26815 Tendedero Plegable Pro: actual 900/139 -> PDF 900/900
UPDATE public.productos SET precio_regular = 900, precio_oferta = 900 WHERE codigo = '26815';

-- 24601 Tendedero Plegable 32: actual 900/169 -> PDF 169/169
UPDATE public.productos SET precio_regular = 169, precio_oferta = 169 WHERE codigo = '24601';

-- 23107 Quita Max Roller: actual 179/129 -> PDF 129/129
UPDATE public.productos SET precio_regular = 129, precio_oferta = 129 WHERE codigo = '23107';

-- 25976 Limpia WC: actual 179/159 -> PDF 159/159
UPDATE public.productos SET precio_regular = 159, precio_oferta = 159 WHERE codigo = '25976';

-- 24600 Set Limpia WC: actual 6490/219 -> PDF 219/219
UPDATE public.productos SET precio_regular = 219, precio_oferta = 219 WHERE codigo = '24600';

-- 22253 Brazo Limpia Fácil: actual 8990/8990 -> PDF 89.9/89.9
UPDATE public.productos SET precio_regular = 89.9, precio_oferta = 89.9 WHERE codigo = '22253';

-- 23178 Cloritas: actual 5490/5490 -> PDF 54.9/54.9
UPDATE public.productos SET precio_regular = 54.9, precio_oferta = 54.9 WHERE codigo = '23178';

-- 24111 Sticks Tuberías: actual 6490/6490 -> PDF 64.9/64.9
UPDATE public.productos SET precio_regular = 64.9, precio_oferta = 64.9 WHERE codigo = '24111';

-- 24163 Limpia Lavadora: actual 6490/119 -> PDF 119/119
UPDATE public.productos SET precio_regular = 119, precio_oferta = 119 WHERE codigo = '24163';

-- 26121 Tabs Limpia Vidrios: actual 4990/4990 -> PDF 49.9/49.9
UPDATE public.productos SET precio_regular = 49.9, precio_oferta = 49.9 WHERE codigo = '26121';

-- 26102 Tabs Desengrasante: actual 5490/4990 -> PDF 54.9/54.9
UPDATE public.productos SET precio_regular = 54.9, precio_oferta = 54.9 WHERE codigo = '26102';

-- 26101 Extensible Microfibra Punta flexible: actual 8990/8990 -> PDF 89.9/89.9
UPDATE public.productos SET precio_regular = 89.9, precio_oferta = 89.9 WHERE codigo = '26101';

-- 23186 Jalador Extensible: actual 179/109 -> PDF 109/109
UPDATE public.productos SET precio_regular = 109, precio_oferta = 109 WHERE codigo = '23186';

-- 26116 Set Fibra Esponja: actual 7990/7990 -> PDF 79.9/79.9
UPDATE public.productos SET precio_regular = 79.9, precio_oferta = 79.9 WHERE codigo = '26116';

-- 26108 Aqua Pop: actual 8990/8990 -> PDF 89.9/89.9
UPDATE public.productos SET precio_regular = 89.9, precio_oferta = 89.9 WHERE codigo = '26108';

-- 22128 Cepillo Flex: actual 6990/6990 -> PDF 69.9/69.9
UPDATE public.productos SET precio_regular = 69.9, precio_oferta = 69.9 WHERE codigo = '22128';

-- 26885 Cepillo Flex: actual 6990/6990 -> PDF 69.9/69.9
UPDATE public.productos SET precio_regular = 69.9, precio_oferta = 69.9 WHERE codigo = '26885';

-- 26817 Aqua: actual 199/179 -> PDF 179/179
UPDATE public.productos SET precio_regular = 179, precio_oferta = 179 WHERE codigo = '26817';

-- 26818 Cubre Zapatos Aqua: actual 179/149 -> PDF 149/149
UPDATE public.productos SET precio_regular = 149, precio_oferta = 149 WHERE codigo = '26818';

-- 26704 Vaso Dúo: actual 9990/9990 -> PDF 149/149
UPDATE public.productos SET precio_regular = 149, precio_oferta = 149 WHERE codigo = '26704';

-- 26771 PASTILLERO: actual 5990/159 -> PDF 59.9/59.9
UPDATE public.productos SET precio_regular = 59.9, precio_oferta = 59.9 WHERE codigo = '26771';

-- 25436 Pasti Semanal Pro: actual 5990/159 -> PDF 159/159
UPDATE public.productos SET precio_regular = 159, precio_oferta = 159 WHERE codigo = '25436';

-- 26134 Baggy Tech: actual 650/149 -> PDF 149/149
UPDATE public.productos SET precio_regular = 149, precio_oferta = 149 WHERE codigo = '26134';

-- 26810 Porta Cepillos Lila: actual 6990/6990 -> PDF 69.9/69.9
UPDATE public.productos SET precio_regular = 69.9, precio_oferta = 69.9 WHERE codigo = '26810';

-- 23228 Cápsula Perfume  Max: actual 6990/129 -> PDF 129/129
UPDATE public.productos SET precio_regular = 129, precio_oferta = 129 WHERE codigo = '23228';

-- 26133 Retoque Express: actual 9990/129 -> PDF 99.9/99.9
UPDATE public.productos SET precio_regular = 99.9, precio_oferta = 99.9 WHERE codigo = '26133';

-- 26789 Protecti Derrames: actual 9990/6990 -> PDF 69.9/69.9
UPDATE public.productos SET precio_regular = 69.9, precio_oferta = 69.9 WHERE codigo = '26789';

-- 26702 Basurero Click: actual 6990/249 -> PDF 69.9/69.9
UPDATE public.productos SET precio_regular = 69.9, precio_oferta = 69.9 WHERE codigo = '26702';

-- 26780 Almohada Infinita: actual 6990/249 -> PDF 249/249
UPDATE public.productos SET precio_regular = 249, precio_oferta = 249 WHERE codigo = '26780';

-- 26779 Lumi Espejo Auto: actual 9990/249 -> PDF 249/249
UPDATE public.productos SET precio_regular = 249, precio_oferta = 249 WHERE codigo = '26779';

-- 23796 Soporte Cel Lux: actual 8990/129 -> PDF 89.9/89.9
UPDATE public.productos SET precio_regular = 89.9, precio_oferta = 89.9 WHERE codigo = '23796';

-- 26762 Soporte Movi Cel: actual 8990/109 -> PDF 109/109
UPDATE public.productos SET precio_regular = 109, precio_oferta = 109 WHERE codigo = '26762';

-- 26748 Better Carrito Pro: actual 1600/999 -> PDF 1600/1600
UPDATE public.productos SET precio_regular = 1600, precio_oferta = 1600 WHERE codigo = '26748';

-- 26045 Cervetarro: actual 349/249 -> PDF 349/349
UPDATE public.productos SET precio_regular = 349, precio_oferta = 349 WHERE codigo = '26045';

-- 26747 Destapa Porta Bebidas: actual 349/249 -> PDF 249/249
UPDATE public.productos SET precio_regular = 249, precio_oferta = 249 WHERE codigo = '26747';

-- 26821 Banquito: actual 449/179 -> PDF 449/449
UPDATE public.productos SET precio_regular = 449, precio_oferta = 449 WHERE codigo = '26821';

-- 26024 Moldi Paletas: actual 7990/7990 -> PDF 79.9/79.9
UPDATE public.productos SET precio_regular = 79.9, precio_oferta = 79.9 WHERE codigo = '26024';

-- 25038 Estación Fresh: actual 259/159 -> PDF 259/259
UPDATE public.productos SET precio_regular = 259, precio_oferta = 259 WHERE codigo = '25038';

-- 26547 Better Raspados: actual 299/189 -> PDF 299/299
UPDATE public.productos SET precio_regular = 299, precio_oferta = 299 WHERE codigo = '26547';

-- 24043 Jarra Smart: actual 299/189 -> PDF 189/189
UPDATE public.productos SET precio_regular = 189, precio_oferta = 189 WHERE codigo = '24043';

-- 26131 Bolsa Barbie™ 70s: actual 499/219 -> PDF 499/499
UPDATE public.productos SET precio_regular = 499, precio_oferta = 499 WHERE codigo = '26131';

-- 26842 Vaso: actual 499/219 -> PDF 219/219
UPDATE public.productos SET precio_regular = 219, precio_oferta = 219 WHERE codigo = '26842';

-- 26403 Cuadri Organizador: actual 219/159 -> PDF 219/219
UPDATE public.productos SET precio_regular = 219, precio_oferta = 219 WHERE codigo = '26403';

-- 23607 Maleta Mascota Go: actual 499/219 -> PDF 499/499
UPDATE public.productos SET precio_regular = 499, precio_oferta = 499 WHERE codigo = '23607';

-- 23345 Cambia Pañales Baby: actual 800/599 -> PDF 349/349
UPDATE public.productos SET precio_regular = 349, precio_oferta = 349 WHERE codigo = '23345';

-- 25134 Multi Cepillo: actual 349/219 -> PDF 179/179
UPDATE public.productos SET precio_regular = 179, precio_oferta = 179 WHERE codigo = '25134';

-- 25804 Multi Repisas Bambú: actual 899/599 -> PDF 499/499
UPDATE public.productos SET precio_regular = 499, precio_oferta = 499 WHERE codigo = '25804';

-- 26527 Rebana Chef: actual 499/169 -> PDF 169/169
UPDATE public.productos SET precio_regular = 169, precio_oferta = 169 WHERE codigo = '26527';

-- 24855 Tri Charola: actual 499/169 -> PDF 549/549
UPDATE public.productos SET precio_regular = 549, precio_oferta = 549 WHERE codigo = '24855';

