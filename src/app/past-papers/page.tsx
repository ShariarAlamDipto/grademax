
"use client"
import React from "react"

import Link from "next/link"

const subjects = {
  IGCSE: [
    { name: "Physics", color: "#F4A261" },         // Soft Amber
    { name: "Chemistry", color: "#CDB4DB" },       // Muted Lavender
    { name: "Biology", color: "#90BE6D" },         // Sage Green
    { name: "English Language B", color: "#FFB4A2" }, // Blush Pink
    { name: "ICT", color: "#E76F51" },             // Dusty Rose Red
    { name: "Maths A", color: "#A8DADC" },         // Calm Sky Blue
    { name: "Maths B", color: "#457B9D" },         // Steel Blue
  ],
  IAL: [
    { name: "Maths", color: "#A8DADC" },
    { name: "Physics", color: "#F4A261" },
    { name: "Chemistry", color: "#CDB4DB" },
  ],
}

export default function PastPapersPage() {
  return (
    <main className="min-h-screen bg-black text-white px-6 py-12">
      <h1 className="text-center text-4xl font-extrabold mb-10">
        Past Papers
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10 max-w-6xl mx-auto">
        {/* IGCSE */}
        <div className="bg-[#0f0f0f] rounded-2xl p-6 shadow-lg shadow-black/40">
          <h2 className="text-2xl font-bold mb-6 text-center">IGCSE</h2>
            <div className="flex flex-col gap-0">
              {subjects.IGCSE.map((subj, idx) => (
                <React.Fragment key={subj.name}>
                  <Link href={`/past-papers/${subj.name.toLowerCase().replace(/\s+/g, "-")}`}> 
                    <button
                      className="w-full py-3 rounded-lg text-white font-semibold 
                                 transition-all duration-300 shadow-md 
                                 hover:brightness-110 hover:shadow-lg hover:scale-[1.02]"
                      style={{ backgroundColor: subj.color }}
                    >
                      {subj.name}
                    </button>
                  </Link>
                  {idx < subjects.IGCSE.length - 1 && (
                    <div className="my-3 w-full border-t border-white/10" />
                  )}
                </React.Fragment>
              ))}
            </div>
        </div>

        {/* IAL */}
        <div className="bg-[#0f0f0f] rounded-2xl p-6 shadow-lg shadow-black/40">
          <h2 className="text-2xl font-bold mb-6 text-center">IAL</h2>
            <div className="flex flex-col gap-0">
              {subjects.IAL.map((subj, idx) => (
                <React.Fragment key={subj.name}>
                  <Link href={`/past-papers/${subj.name.toLowerCase().replace(/\s+/g, "-")}`}> 
                    <button
                      className="w-full py-3 rounded-lg text-white font-semibold 
                                 transition-all duration-300 shadow-md 
                                 hover:brightness-110 hover:shadow-lg hover:scale-[1.02]"
                      style={{ backgroundColor: subj.color }}
                    >
                      {subj.name}
                    </button>
                  </Link>
                  {idx < subjects.IAL.length - 1 && (
                    <div className="my-3 w-full border-t border-white/10" />
                  )}
                </React.Fragment>
              ))}
            </div>
        </div>
      </div>
    </main>
  )
}
