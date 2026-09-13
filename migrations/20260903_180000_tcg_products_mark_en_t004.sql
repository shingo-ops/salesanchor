-- PARITY-03 Phase 3: tcg_products に mark / english_title 列を追加し
-- GAS 商品マスタV2（268件）から充填する（冪等）。
--
-- 充填率（2026-09-03 シート直読み）:
--   mark:          239/268 (89.2%)  NULL=29件 = GAS が空欄または '-'
--   english_title: 251/268 (93.7%)  NULL=17件 = 同上
--
-- 投入元: clasp run y1406DumpProductMasterV2Page (2026-09-03 取得、3バッチ合計268件)
-- 取得コマンド:
--   cd ~/sqr07_work
--   clasp run y1406DumpProductMasterV2Page --params '[1, 90]'
--   clasp run y1406DumpProductMasterV2Page --params '[91, 90]'
--   clasp run y1406DumpProductMasterV2Page --params '[181, 90]'

DO $body$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260903_180000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- mark 列追加（既存なら skip）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema
          AND table_name   = 'tcg_products'
          AND column_name  = 'mark'
    ) THEN
        EXECUTE format('ALTER TABLE %I.tcg_products ADD COLUMN mark VARCHAR', _schema);
        RAISE NOTICE 'migration 20260903_180000: mark column added';
    ELSE
        RAISE NOTICE 'migration 20260903_180000: mark column already exists, skipping';
    END IF;

    -- english_title 列追加（既存なら skip）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema
          AND table_name   = 'tcg_products'
          AND column_name  = 'english_title'
    ) THEN
        EXECUTE format('ALTER TABLE %I.tcg_products ADD COLUMN english_title VARCHAR', _schema);
        RAISE NOTICE 'migration 20260903_180000: english_title column added';
    ELSE
        RAISE NOTICE 'migration 20260903_180000: english_title column already exists, skipping';
    END IF;

    -- GAS 商品マスタV2 から 268件を充填（既存値は上書き・冪等）
    EXECUTE format($dml$
        UPDATE %I.tcg_products AS t
        SET
            mark          = v.mark,
            english_title = v.english_title
        FROM (VALUES
        ('PM0001', 'MMD', 'Monster ball Miror duplicate bulk set'),
        ('PM0002', 'RRD', 'RR duplicate bulk set'),
        ('PM0003', 'RRRD', 'RRR duplicate bulk set'),
        ('PM0004', 'SD', 'S duplicate bulk set'),
        ('PM0005', 'SRD', 'SR duplicate bulk set'),
        ('PM0006', 'SARD', 'SAR card (duplicate)'),
        ('PM0007', 'ARCHRD', 'AR/CHR card (no duplicate)'),
        ('PM0008', 'ARCHRD', 'AR/CHR  card (duplicate)'),
        ('PM0009', 'ARCHRD', 'AR/CHR card (max 2 duplicates)'),
        ('PM0010', 'ARND', 'AR card (no-duplicate)'),
        ('PM0011', 'ARD', 'AR card (duplicate)'),
        ('PM0012', 'SM1S', 'Collection Sun'),
        ('PM0013', 'SM1M', 'Collection Moon'),
        ('PM0014', 'SM1+', 'Sun & Moon'),
        ('PM0015', 'SM2L', 'Islands Await You'),
        ('PM0016', 'SM2K', 'Alolan Moonlight'),
        ('PM0017', 'SM2+', 'Beyond the New Trial'),
        ('PM0018', 'SM3H', 'Dark Devourers'),
        ('PM0019', 'SM3K', 'Did You See the Fighting Rainbow?'),
        ('PM0020', 'SM3+', 'Shining Legends'),
        ('PM0021', 'SM4S', 'Awakened Heroes'),
        ('PM0022', 'SM4A', 'Transdimensional Beast'),
        ('PM0023', 'SM4+', 'GX Battle Boost'),
        ('PM0024', 'SM5M', 'Ultra Sun'),
        ('PM0025', 'SM5L', 'Ultra Moon'),
        ('PM0026', 'SM5+', 'Ultra Force'),
        ('PM0027', 'SM6', 'Forbidden Light'),
        ('PM0028', 'SM6a', 'Dragon Storm'),
        ('PM0029', 'SM6b', 'Champion Road'),
        ('PM0030', 'SM7', 'Celestial Storm'),
        ('PM0031', 'SM7a', 'Thunderclap Spark'),
        ('PM0032', 'SM7b', 'Fairy Rise'),
        ('PM0033', 'SM8', 'Thunderclap Spark'),
        ('PM0034', 'SM8a', 'Dark Order'),
        ('PM0035', 'SM8b', 'GX Ultra Shiny'),
        ('PM0036', 'SM9', 'Night Unison'),
        ('PM0037', 'SM9b', 'Full Metal Wall'),
        ('PM0038', 'SM9a', 'Double Blaze'),
        ('PM0039', 'SM10', 'GG End'),
        ('PM0040', 'SM10b', 'Detective Pikachu'),
        ('PM0041', 'SM10a', 'Sky Legend'),
        ('PM0042', 'SM11', 'Miracle Twin'),
        ('PM0043', 'SM11a', 'Remix Bout'),
        ('PM0044', 'SM11b', 'Dream League'),
        ('PM0045', 'SM12', 'Alter Genesis'),
        ('PM0046', 'SM12a', 'Tag Team GX All Stars'),
        ('PM0047', 'S1W', 'Sword'),
        ('PM0048', 'S1H', 'Shield'),
        ('PM0049', 'S1a', 'VMAX Rising'),
        ('PM0050', 'S2', 'Rebel Clash'),
        ('PM0051', 'S2a', 'Explosive Walker'),
        ('PM0052', 'S3', 'Infinity Zone'),
        ('PM0053', 'S3a', 'Legendary Heartbeat'),
        ('PM0054', 'S4', 'Astonishing Volt Tackle'),
        ('PM0055', 'S4a', 'Shiny Star V'),
        ('PM0056', 'SP', 'Special Box Kanazawa'),
        ('PM0057', 'S5R', 'Rapid Strike Master'),
        ('PM0058', 'S5I', 'Single Strike Master'),
        ('PM0059', 'S5a', 'Matchless Fighters'),
        ('PM0060', 'S6H', 'Silver Lance'),
        ('PM0061', 'S6K', 'Jet-Black Geist'),
        ('PM0062', 'S6a', 'Eevee Heroes'),
        ('PM0063', 'SP', 'Eevee Heroes Eevee''s Set'),
        ('PM0064', 'SGG', 'High Class Deck Gangar VMAX'),
        ('PM0065', 'SGI', 'High Class Deck Intereon VMAX'),
        ('PM0066', 'SGD', 'High Class Deck Double box Gangar VMAX & Intereon VMAX'),
        ('PM0067', 'S7R', 'Blue Sky Stream'),
        ('PM0068', 'S7D', 'Skyscraping Perfection'),
        ('PM0069', 'SP', 'Pokémon Card Game Stamp Box - Beauty Back Moon and Pikachu'),
        ('PM0070', 'S8', 'Fusion Arts'),
        ('PM0071', 'S8a', '25th Anniversary Collection'),
        ('PM0072', 'PROMO', '25th Anniversary Collection Promo pack'),
        ('PM0073', 'SP', '25th Aniniversary Golden Box'),
        ('PM0074', 'S8b', 'VMAX Climax'),
        ('PM0075', 'S9', 'Star Birth'),
        ('PM0076', 'S9a', 'Battle Region'),
        ('PM0077', 'S10P', 'Space Juggler'),
        ('PM0078', 'S10D', 'Time Gazer'),
        ('PM0079', 'S10a', 'Dark Phantasma'),
        ('PM0080', 'S10b', 'Pokémon GO'),
        ('PM0081', 'S11', 'Lost Abyss'),
        ('PM0082', 'OP-01', 'ROMANCE DAWN'),
        ('PM0083', 'S11a', 'Incandescent Arcana'),
        ('PM0084', 'S12', 'Paradigm Trigger'),
        ('PM0085', 'OP-02', 'PARAMOUNT WAR'),
        ('PM0086', NULL, 'Precious Collector Box Sword & Shield'),
        ('PM0087', 'S12a', 'VSTAR Universe'),
        ('PM0088', 'SV1S', 'Scarlet ex'),
        ('PM0089', 'SV1V', 'Violet ex'),
        ('PM0090', 'SVAM', 'Starter Set ex Sprigatito & Lucario ex'),
        ('PM0091', 'SVAL', 'Starter Set ex Fuecoco & Ampharos ex'),
        ('PM0092', 'SVAW', 'Starter Set ex Quaxly & Mimikyu ex'),
        ('PM0093', 'SVB', 'Premium Trainer Box ex'),
        ('PM0094', 'OP-03', 'PILLARS OF STRENGTH'),
        ('PM0095', 'SV1a', 'Triplet Beat'),
        ('PM0096', 'SVC', 'Starter Set ex Pikachu ex & Pawmot'),
        ('PM0097', 'SV2P', 'Snow Hazard'),
        ('PM0098', 'SV2D', 'Clay Burst'),
        ('PM0099', 'SP', 'Snow Hazard & Clay Burst Pokemon Center Gym Set'),
        ('PM0100', 'SVP1', 'ex Special Set'),
        ('PM0101', 'PROMO', 'Yu Nagaba Pikachu Promo card'),
        ('PM0102', 'PROMO', 'Yu Nagaba Eevee Promo card'),
        ('PM0103', 'OP-04', 'KINGDOMS OF INTRIGUE'),
        ('PM0104', 'SV2a', 'Pokemon card 151'),
        ('PM0105', 'SV3', 'Ruler of the Black Flame'),
        ('PM0106', 'WCS23', '2023 Yokohama Commemorative Deck Pikachu'),
        ('PM0107', 'SVF', 'Deck Build Box Ruler of the Black Flame'),
        ('PM0108', 'PROMO', 'TANTO Promo Card Pack'),
        ('PM0109', 'SV3a', 'Raging Surf'),
        ('PM0110', 'SVEM', 'Starter Set Terastal Mewtwo ex'),
        ('PM0111', 'SVEL', 'Starter Set Terastal Skeledirge ex'),
        ('PM0112', 'PROMO', 'Detective Pikachu Promo'),
        ('PM0113', 'SV4K', 'Ancient Roar'),
        ('PM0114', 'SV4M', 'Future Flash'),
        ('PM0115', 'SVG', 'Special Deck Set ex Venusaur, Charizard & Blastoise'),
        ('PM0116', NULL, 'Pokemon card game Classic'),
        ('PM0117', 'SV4a', 'Shiny Treasure ex'),
        ('PM0118', 'OP-05', 'AWAKENING OF THE NEW ERA'),
        ('PM0119', 'SV5M', 'Cyber Judge'),
        ('PM0120', 'SV5K', 'Wild Force'),
        ('PM0121', 'SVHK', 'Starter Deck & Build Set Ancient Koraidon ex'),
        ('PM0122', 'SVHM', 'Starter Deck & Build Set Future Miraidon ex'),
        ('PM0123', 'EB-01', 'MEMORIAL COLLECTION'),
        ('PM0124', 'FB01', 'Awakened Pulse'),
        ('PM0125', 'SVI', 'Battle Academy'),
        ('PM0126', 'SVI', 'Battle Academy Anytime, Anywhere'),
        ('PM0127', 'OP-06', 'TWO LEGENDS'),
        ('PM0128', 'SV5a', 'Crimson Haze'),
        ('PM0129', 'SV6', 'Mask of Change'),
        ('PM0130', 'FB02', 'Blazing Aura'),
        ('PM0131', 'SVJL', 'Battle Master Deck Terastal Charizard ex'),
        ('PM0132', 'SVJP', 'Battle Master Deck Chien-Pao ex'),
        ('PM0133', 'SV6a', 'Night Wanderer'),
        ('PM0134', 'OP-07', '500 YEARS IN THE FUTURE'),
        ('PM0135', 'SV7', 'Stellar Miracle'),
        ('PM0136', 'SVK', 'Deck Build Box Stellar Miracle'),
        ('PM0137', 'PRB-01', 'THE BEST'),
        ('PM0138', 'FB03', 'Raging Roar'),
        ('PM0139', 'SVLN', 'Starter Set Teratype: Stellar Sylveon ex'),
        ('PM0140', 'SVLS', 'Starter Set Teratype: Stellar Ceruledge ex'),
        ('PM0141', 'OP-09', 'THE NEW EMPEROR'),
        ('PM0142', 'SV7a', 'Paradise Dragona'),
        ('PM0143', 'OP-08', 'TWO LEGENDS'),
        ('PM0144', 'SV8', 'Super Electric Breaker'),
        ('PM0145', 'FB04', 'Ultra Limit'),
        ('PM0146', 'SVM', 'Start Deck Generations (various types)'),
        ('PM0147', 'SV8a', 'Terastal Festival ex'),
        ('PM0148', 'SV9', 'Battle Partners'),
        ('PM0149', 'PROMO', 'Iono Promo'),
        ('PM0150', 'SVN', 'Deck Build Box Battle Partners'),
        ('PM0151', NULL, 'Collection File Set N'),
        ('PM0152', NULL, 'Collection File Set Lillie'),
        ('PM0153', 'EB-02', 'ANIME 25th ANNIVERSARY'),
        ('PM0154', 'FB05', 'New Adventure'),
        ('PM0155', 'SVOM', 'Starter Set ex Marnie’s Morpeko & Grimmsnarl ex'),
        ('PM0156', 'SVOD', 'Starter Set ex Steven’s Beldum & Metagross ex'),
        ('PM0157', 'OP-11', 'A FIST OF DIVINE SPEED'),
        ('PM0158', 'SV9a', 'Heat Wave Arena'),
        ('PM0159', 'PROMO', 'Heat wave arena Promo card'),
        ('PM0160', 'OP-10', 'ROYAL BLOOD'),
        ('PM0161', 'SV10', 'Glory of Team Rocket'),
        ('PM0162', 'OS01', 'Yuzusoft'),
        ('PM0163', 'OS02', 'Gushing over Magical Girls'),
        ('PM0164', 'FB06', 'Rivals Clash'),
        ('PM0165', 'SV11B(DX)', 'Black Bolt DX'),
        ('PM0166', 'SV11W(DX)', 'White Flare DX'),
        ('PM0167', 'SV11B', 'Black Bolt'),
        ('PM0168', 'SV11W', 'White Flare'),
        ('PM0169', 'OS03', 'HARUKAZE'),
        ('PM0170', 'SB01', 'MANGA BOOSTER 01'),
        ('PM0171', 'GD01', 'Newtype Rising'),
        ('PM0172', 'PRB-02', 'THE BEST vol.2'),
        ('PM0173', 'M1L', 'Mega Brave'),
        ('PM0174', 'M1S', 'Mega Symphonia'),
        ('PM0175', 'MA', 'Premium Trainer Box MEGA'),
        ('PM0176', 'PCJ', 'Mega Symphonia Pokemon Center set'),
        ('PM0177', 'PCJ', 'Mega Brave Pokemon Center set'),
        ('PM0178', 'PROMO', 'Pikachu McDonald''s Promo'),
        ('PM0179', 'PROMO', 'ONE PIECE DAY’25 Promo'),
        ('PM0180', 'OP-12', 'LEGACY OF THE MASTER'),
        ('PM0181', 'OP-13', 'CARRYING ON HIS WILL'),
        ('PM0182', 'SP', 'Special Box Tohoku'),
        ('PM0183', 'OS04', 'Interspecies Reviewers'),
        ('PM0184', 'MBG', 'MEGA Starter Set Mega Gengar ex'),
        ('PM0185', 'MBD', 'MEGA Starter Set Mega Diancie ex'),
        ('PM0186', 'SP', 'Special Box Hiroshima'),
        ('PM0187', 'FB07', 'Wish for Shenron'),
        ('PM0188', 'M2', 'Inferno X'),
        ('PM0189', 'SP', 'Special Box Fukuoka'),
        ('PM0190', 'PROMO', 'One Piece Magazine Promo card'),
        ('PM0191', 'PROMO', 'Promotion card set 2025'),
        ('PM0192', 'GD02', 'Dual Impact'),
        ('PM0193', 'EB-03', 'HEROINES EDITION'),
        ('PM0194', 'OS05', 'sprite'),
        ('PM0195', 'SB02', 'MANGA BOOSTER 02'),
        ('PM0196', 'OP-14', 'THE AZURE SEA’S SEVEN'),
        ('PM0197', 'FB08', 'SAIYAN’s PRIDE'),
        ('PM0198', 'M3', 'MEGA Dream ex'),
        ('PM0199', 'PROMO', 'ONE PIECE BASE SHOP Limited card collection Vol.1'),
        ('PM0200', 'MBB', 'MEGA Start Deck 100 Battle Collection'),
        ('PM0201', 'OS06', 'The Pillow'),
        ('PM0202', 'M3', 'Nihil Zero'),
        ('PM0203', 'PROMO', 'MEGA Special Card Set Mega Gallade ex'),
        ('PM0204', 'OS07', 'Lose&Whisp'),
        ('PM0205', 'GD03', 'Steel Requiem'),
        ('PM0206', 'EB-04', 'EGGHEAD CRISIS'),
        ('PM0207', 'OP-15', 'Godland Adventure'),
        ('PM0208', 'EX13BT', 'Gakuen Idolmaster Vol.2'),
        ('PM0209', 'M4', 'Ninja Spinner'),
        ('PM0210', NULL, 'D.C. Re:tune'),
        ('PM0211', 'UA51BT', 'Solo Leveling'),
        ('PM0212', 'SV2a', 'Pokemon 151 CN vol.4 slim'),
        ('PM0213', 'SV2a', 'Pokemon 151 CN vol.4 jumbo'),
        ('PM0214', 'SV2a', 'Pokemon 151 CN vol.1 slim'),
        ('PM0215', 'SV2a', 'Pokemon 151 CN Gift Box Starter Set (3-box)'),
        ('PM0216', 'SV2a', 'Pokemon 151 CN Gift Box Bulbasaur'),
        ('PM0217', 'SV2a', 'Pokemon 151 CN Gift Box Charmander'),
        ('PM0218', 'SV2a', 'Pokemon 151 CN Gift Box Squirtle'),
        ('PM0219', 'M6', NULL),
        ('PM0220', 'M5', NULL),
        ('PM0221', 'XY2', NULL),
        ('PM0222', 'OP-16', NULL),
        ('PM0223', 'LOCH', NULL),
        ('PM0224', 'LOCR', NULL),
        ('PM0225', 'PC02BT', NULL),
        ('PM0226', 'FB09', NULL),
        ('PM0227', NULL, NULL),
        ('PM0228', NULL, NULL),
        ('PM0229', NULL, 'Retro card bulk'),
        ('PM0230', 'OSK', 'Oshi no Ko Trial Deck'),
        ('PM0231', 'PROMO', 'Victini red promo'),
        ('PM0232', NULL, 'The First Chapter'),
        ('PM0233', NULL, 'Rise of the Floodborn'),
        ('PM0234', NULL, 'Into the Inklands'),
        ('PM0235', NULL, 'Ursula''s Return'),
        ('PM0236', NULL, 'Shimmering Skies'),
        ('PM0237', NULL, 'Azurite Sea'),
        ('PM0238', NULL, 'Archazia''s Island'),
        ('PM0239', NULL, 'Reign of Jafar'),
        ('PM0240', NULL, 'Fabled'),
        ('PM0241', NULL, 'Whispers in the Well'),
        ('PM0242', NULL, 'Winterspell'),
        ('PM0243', NULL, 'Wilds Unknown'),
        ('PM0244', NULL, 'Attack of the Vine!'),
        ('PM0245', NULL, 'Hyperia City'),
        ('PM0246', 'LEDE', 'Legacy of Destruction'),
        ('PM0247', 'INFO', 'The Infinite Forbidden'),
        ('PM0248', 'ROTA', 'Rage of the Abyss'),
        ('PM0249', 'SUDA', 'Supreme Darkness'),
        ('PM0250', 'ALIN', 'Alliance Insight'),
        ('PM0251', 'DUAD', 'Duelist''s Advance'),
        ('PM0252', 'DOOD', 'Doom of Dimensions'),
        ('PM0253', 'BPRO', 'Burst Protocol'),
        ('PM0254', 'BLZD', 'Blazing Dominion'),
        ('PM0255', 'CORI', 'Chaos Origins'),
        ('PM0256', 'QCCU', 'Quarter Century Chronicle side:Unity'),
        ('PM0257', 'QCCP', 'Quarter Century Chronicle side:Pride'),
        ('PM0258', 'QCDB', 'Quarter Century Duelist Box'),
        ('PM0259', 'QCAC', 'Quarter Century Art Collection'),
        ('PM0260', 'BETB', NULL),
        ('PM0261', NULL, NULL),
        ('PM0262', NULL, NULL),
        ('PM0263', NULL, NULL),
        ('PM0264', NULL, NULL),
        ('PM0265', NULL, NULL),
        ('PM0266', 'OP-17', 'The World''s Strongest Warriors'),
        ('PM0267', NULL, NULL),
        ('PM0268', NULL, '4th Anniversary! Four Emperors Treasure Get Campaign Pack')
        ) AS v(code, mark, english_title)
        WHERE t.code = v.code
    $dml$, _schema);

    RAISE NOTICE 'migration 20260903_180000: mark/english_title UPDATE complete (268 rows)';
END;
$body$;
