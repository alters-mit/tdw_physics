from tdw.librarian import MaterialLibrarian, MaterialRecord

if __name__ == '__main__':

    c = MaterialLibrarian()
    ms = c.get_material_types()
    print(ms)
    for m in ms:
        more_ms = c.get_all_materials_of_type(m)
        print(m, [_m.name for _m in more_ms])
