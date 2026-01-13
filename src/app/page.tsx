"use client";

import Link from "next/link";
import { FaPlus, FaHistory } from "react-icons/fa";

export default function Home() {
  return (
    <main className="min-h-screen p-6 max-w-4xl mx-auto">
      <header className="mb-8 pt-8">
        <h1 className="text-4xl font-bold text-primary-600 mb-2">
          VoxDocs Pflegedienst
        </h1>
        <p className="text-gray-600">
          Dokumentation für Pflegetermine
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <Link
          href="/appointment/new"
          className="card hover:shadow-lg transition-shadow duration-200 cursor-pointer group"
        >
          <div className="flex items-center gap-4">
            <div className="bg-primary-100 text-primary-600 p-4 rounded-lg group-hover:bg-primary-200 transition-colors">
              <FaPlus size={32} />
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-1">Neuer Termin</h2>
              <p className="text-gray-600">
                Starte einen neuen Pflegetermin
              </p>
            </div>
          </div>
        </Link>

        <Link
          href="/appointments"
          className="card hover:shadow-lg transition-shadow duration-200 cursor-pointer group"
        >
          <div className="flex items-center gap-4">
            <div className="bg-gray-100 text-gray-600 p-4 rounded-lg group-hover:bg-gray-200 transition-colors">
              <FaHistory size={32} />
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-1">Verlauf</h2>
              <p className="text-gray-600">
                Alle Termine ansehen
              </p>
            </div>
          </div>
        </Link>
      </div>
    </main>
  );
}
