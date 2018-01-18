from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.constants import SH_FLAGS


class Elf:
    def __init__(self, filename):
        self.fileobj = open(filename, "rb")
        self.elffile = ELFFile(self.fileobj)

    def update_backend(self, backend):
        with backend.db:
            # TODO: use segments if no sections
            for section in self.elffile.iter_sections():
                if section["sh_flags"] & SH_FLAGS.SHF_ALLOC:
                    name = section.name
                    addr = section["sh_addr"]
                    data = section.data()

                    backend.sections.add(addr, data, name=name)

            for sym in self.iter_symbols():
                if not sym.name:
                    continue

                section_index = sym["st_shndx"]
                # TODO
                if isinstance(section_index, str):
                    continue

                section = self.elffile.get_section(section_index)
                section_addr = section["sh_addr"]
                sym_addr = section_addr + sym["st_value"]

                backend.symbols.add(sym_addr, name=sym.name)

    def iter_symbols(self):
        for section in self.elffile.iter_sections():
            if isinstance(section, SymbolTableSection):
                yield from section.iter_symbols()


def load_elf(backend, filename):
    elf = Elf(filename)
    elf.update_backend(backend)
