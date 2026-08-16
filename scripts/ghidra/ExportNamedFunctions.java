/*
 * Export selected decompiled functions from the current Ghidra program.
 *
 * Headless usage:
 *   analyzeHeadless <project-dir> <project-name> \
 *     -process <program> \
 *     -scriptPath <this-directory> \
 *     -postScript ExportNamedFunctions.java <output-file> <name-fragment>...
 */
//@category Quantum2626

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class ExportNamedFunctions extends GhidraScript {
	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length < 2) {
			printerr("Usage: ExportNamedFunctions.java <output-file> <name-fragment>...");
			return;
		}

		File output = new File(args[0]);
		DecompInterface decompiler = new DecompInterface();
		decompiler.toggleCCode(true);
		decompiler.toggleSyntaxTree(true);

		if (!decompiler.openProgram(currentProgram)) {
			printerr("Could not initialize the decompiler for " + currentProgram.getName());
			return;
		}

		int matched = 0;
		try (PrintWriter writer = new PrintWriter(
			new BufferedWriter(new FileWriter(output)))) {
			for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
				String name = function.getName(true);
				if (!matches(name, args)) {
					continue;
				}

				matched++;
				writer.println("/* FUNCTION: " + name);
				writer.println(" * ENTRY: " + function.getEntryPoint());
				writer.println(" */");
				writer.println("/* DISASSEMBLY");
				InstructionIterator instructions =
					currentProgram.getListing().getInstructions(function.getBody(), true);
				while (instructions.hasNext()) {
					Instruction instruction = instructions.next();
					writer.println(instruction.getAddress() + "  " + instruction);
				}
				writer.println("*/");

				DecompileResults result = decompiler.decompileFunction(function, 90, monitor);
				if (result.decompileCompleted() && result.getDecompiledFunction() != null) {
					writer.println(result.getDecompiledFunction().getC());
				}
				else {
					writer.println("/* DECOMPILATION FAILED: " + result.getErrorMessage() + " */");
				}
				writer.println();
			}
		}
		finally {
			decompiler.dispose();
		}

		println("Exported " + matched + " function(s) to " + output.getAbsolutePath());
	}

	private boolean matches(String name, String[] args) {
		for (int i = 1; i < args.length; i++) {
			if (name.contains(args[i])) {
				return true;
			}
		}
		return false;
	}
}
