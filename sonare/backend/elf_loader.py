import sys
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.constants import SH_FLAGS, P_FLAGS
from .backend import Range
from .arch import BaseArch, ArmArch


class Elf:
    def __init__(self, filename):
        self.fileobj = open(filename, "rb")
        self.elffile = ELFFile(self.fileobj)
        self.arch = self.get_arch()

    def get_arch(self):
        elf_arch = self.elffile["e_machine"]

        if elf_arch == "EM_ARM":
            return ArmArch()
        else:
            return BaseArch()

    def update_backend(self, backend):
        arch = self.get_arch()

        with backend.db:
            # TODO: use sections if no segments
            self._load_segments_as_sections(backend)

            for sym in self.iter_symbols():
                if not sym.name:
                    continue

                section_index = sym["st_shndx"]
                # TODO
                if isinstance(section_index, str):
                    continue

                sym_addr = sym["st_value"]
                # TODO: for relocatable files, add section_addr to sym_addr
                # section = self.elffile.get_section(section_index)
                # section_addr = section["sh_addr"]
                # sym_addr += section_addr

                # don't allow zero-length symbols, otherwise range doesn't
                # include anything
                size = max(sym["st_size"], 1)
                sym_end = sym_addr + size

                backend_obj = Range(sym_addr, sym_end, name=sym.name)
                arch.hook_load_symbol(backend_obj)

                backend.symbols.add_obj(backend_obj)

                if sym["st_info"]["type"] == "STT_FUNC":
                    overlaps = list(backend.functions.iter_where_overlaps(
                        backend_obj.start, backend_obj.end))
                    if overlaps:
                        print(
                            f"not adding {backend_obj.name}, it overlaps with"
                            f" {', '.join(other.name for other in overlaps)}",
                            file=sys.stderr)
                    else:
                        backend.functions.add_obj(backend_obj)

    def _load_segments_as_sections(self, backend):
        for segment in self.elffile.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                addr = segment["p_vaddr"]
                data = segment.data()
                backend.sections.add(addr, data)

    def _load_sections_as_sections(self, backend):
        for section in self.elffile.iter_sections():
            if section["sh_flags"] & SH_FLAGS.SHF_ALLOC:
                name = section.name
                addr = section["sh_addr"]
                data = section.data()

                backend.sections.add(addr, data, name=name)

    def iter_symbols(self):
        for section in self.elffile.iter_sections():
            if isinstance(section, SymbolTableSection):
                yield from section.iter_symbols()


def load_elf(backend, filename):
    elf = Elf(filename)
    elf.update_backend(backend)
