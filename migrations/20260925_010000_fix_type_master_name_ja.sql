-- Fix type_master.name_ja: English values → Japanese
-- id=2 (one_piece): "One Piece" → "ワンピース"
-- id=24 (xross_stars): "Xross Stars" → "クロススタァ"

UPDATE public.type_master SET name_ja = 'ワンピース' WHERE id = 2 AND name_ja = 'One Piece';
UPDATE public.type_master SET name_ja = 'クロススタァ' WHERE id = 24 AND name_ja = 'Xross Stars';
