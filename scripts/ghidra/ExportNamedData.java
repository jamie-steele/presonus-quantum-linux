/*
 * Export selected named data symbols from the current Ghidra program.
 *
 * Headless usage:
 *   analyzeHeadless <project-dir> <project-name> \
 *     -process <program> \
 *     -scriptPath <this-directory> \
 *     -postScript ExportNamedData.java <output-file> <bytes> <name-fragment>...
 *
 * Keep output outside the repository when inspecting proprietary binaries.
 */
//@category Quantum2626

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class ExportNamedData extends GhidraScript {
	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length < 3) {
			printerr("Usage: ExportNamedData.java <output-file> <bytes> <name-fragment>...");
			return;
		}

		int byteCount = Integer.decode(args[1]);
		if (byteCount <= 0) {
			printerr("Byte count must be positive");
			return;
		}

		File output = new File(args[0]);
		Memory memory = currentProgram.getMemory();
		AddressSpace space = currentProgram.getAddressFactory().getDefaultAddressSpace();
		int matched = 0;

		try (PrintWriter writer = new PrintWriter(
			new BufferedWriter(new FileWriter(output)))) {
			SymbolIterator symbols = currentProgram.getSymbolTable().getAllSymbols(true);
			while (symbols.hasNext()) {
				Symbol symbol = symbols.next();
				String name = symbol.getName(true);
				if (!matches(name, args))
					continue;

				matched++;
				Address base = symbol.getAddress();
				writer.printf("SYMBOL %s address=%s type=%s%n",
					name, base, symbol.getSymbolType());
				for (int offset = 0; offset < byteCount; offset += Long.BYTES) {
					Address address = base.add(offset);
					byte[] bytes = new byte[Long.BYTES];
					try {
						memory.getBytes(address, bytes);
					}
					catch (Exception exception) {
						writer.printf("+0x%04x unreadable: %s%n",
							offset, exception.getMessage());
						break;
					}

					long value = ByteBuffer.wrap(bytes)
						.order(ByteOrder.LITTLE_ENDIAN).getLong();
					writer.printf("+0x%04x %s qword=0x%016x",
						offset, address, value);
					try {
						Address target = space.getAddress(value);
						Symbol targetSymbol = currentProgram.getSymbolTable()
							.getPrimarySymbol(target);
						String string = readAscii(memory, target, 96);
						if (targetSymbol != null)
							writer.print(" symbol=" + targetSymbol.getName(true));
						if (string != null)
							writer.print(" ascii=\"" + string + "\"");
					}
					catch (Exception ignored) {
						// Most table values are scalars rather than pointers.
					}
					writer.println();
				}
				writer.println();
			}
		}

		println("Exported " + matched + " data symbol(s) to " +
			output.getAbsolutePath());
	}

	private boolean matches(String name, String[] args) {
		for (int i = 2; i < args.length; i++) {
			if (name.contains(args[i]))
				return true;
		}
		return false;
	}

	private String readAscii(Memory memory, Address address, int maximum) {
		StringBuilder builder = new StringBuilder();
		for (int index = 0; index < maximum; index++) {
			byte value;
			try {
				value = memory.getByte(address.add(index));
			}
			catch (Exception exception) {
				return null;
			}
			if (value == 0)
				return builder.length() >= 3 ? builder.toString() : null;
			if (value < 0x20 || value > 0x7e)
				return null;
			builder.append((char)value);
		}
		return null;
	}
}
