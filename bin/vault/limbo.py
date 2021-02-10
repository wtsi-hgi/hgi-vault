





def find_vfpath_without_inode(path: T.Path, vault_root: T.Path, branch) -> T.Path:
    bpath = vault_root / ".vault"/ branch
    for dirname, _, files in os.walk(bpath):
        for file in files:
            vault_file_key = VaultFileKey.Reconstruct(T.Path(dirname, file).relative_to(bpath))
            original_source = vault_root / vault_file_key.source
            if original_source.resolve() == path.resolve():
                vault_file_path = vault_file_key.path
                log.info(f"Found VFK for source {path} at location {vault_file_path}")
                return (bpath / vault_file_path)


                